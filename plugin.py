from __future__ import annotations

import asyncio
import re
from math import ceil
from pathlib import Path, PurePosixPath
from typing import Mapping, AsyncIterator
import json
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from cli_downloader.core.browser_auth import browser_session_cookies, cookie_header_for_url
from cli_downloader.core.models import (
    Asset,
    AssetKind,
    AssetList,
    DownloadStrategy,
    DownloadStrategyPlan,
    ResolveRequest,
    ResolvedItem,
)
from cli_downloader.core.operations import (
    AssetData,
    GalleryData,
    ListItemData,
    ListPageData,
    OperationRequest,
    OperationResult,
    PageInfo,
    ResultKind,
    RouteMatch,
)
from cli_downloader.core.widgets import (
    Action,
    ActionKind,
    Button,
    ListItem,
    ListView,
    Page,
    Pagination,
    SelectionMode,
    Text,
    Title,
)
from cli_downloader.sites.manifest import SiteManifest, site_manifest_from_json_file


_PIXIV_ROOT = "https://www.pixiv.net"
_IMAGE_REFERER = f"{_PIXIV_ROOT}/"


class Plugin:
    site_id = "pixiv"
    display_name = "Pixiv"

    def __init__(self) -> None:
        self._manifest = site_manifest_from_json_file(
            Path(__file__).parent / "manifests" / "site.json"
        )
        self._language = "en"
        self._user_agent = "Mozilla/5.0 CLI-Downloader/0.1"
        self._timeout = 30.0
        self._browser_session: str | None = None
        self._legacy_phpsessid: str | None = None

    def get_manifest_name(self) -> str:
        return "site.json"

    def get_manifest(self) -> SiteManifest:
        return self._manifest

    def configure(
        self,
        settings: Mapping[str, object],
        secrets: Mapping[str, object],
    ) -> None:
        self._language = str(settings.get("language", "en"))
        self._user_agent = str(settings.get("http.user_agent", "Mozilla/5.0 CLI-Downloader/0.1"))
        self._timeout = float(settings.get("http.timeout_seconds", 30.0))
        browser_session = secrets.get("auth.session")
        self._browser_session = str(browser_session) if browser_session else None
        phpsessid = secrets.get("phpsessid")
        self._legacy_phpsessid = str(phpsessid) if phpsessid else None

    def can_handle_url(self, url: str) -> bool:
        return self._manifest.route_url(url) is not None

    def validate_auth_session(self, session: str) -> bool:
        return any(
            cookie["name"] == "PHPSESSID"
            and re.fullmatch(r"[0-9]+_.+", str(cookie["value"])) is not None
            for cookie in browser_session_cookies(session)
        )

    def classify_url(self, url: str) -> RouteMatch | None:
        route = self._manifest.route_url(url)
        if route is None or route.operation_schema is None:
            return None
        return RouteMatch(
            plugin_id="pixiv",
            site_id=self.site_id,
            rule_name=route.rule_name,
            operation_id=route.operation,
            normalized_url=url,
            captures=route.captures,
            parameter_schema={
                name: schema.to_dict() for name, schema in route.operation_schema.params.items()
            },
            required_confirmations=("live_network",),
        )

    async def execute(self, request: OperationRequest) -> OperationResult:
        if request.operation_id == "artwork":
            return await self._artwork_result(request)
        if request.operation_id == "user_illustrations":
            return await self._user_result(request)
        raise ValueError(f"unsupported Pixiv operation: {request.operation_id}")

    async def resolve(self, request: ResolveRequest) -> ResolvedItem:
        route = self.classify_url(request.url)
        if route is None or route.operation_id != "artwork":
            raise ValueError("Pixiv download items must be artwork URLs")
        artwork_id = route.captures["artwork_id"]
        detail = await self._get_json(f"/ajax/illust/{artwork_id}")
        return ResolvedItem(
            site_id=self.site_id,
            source_url=request.url,
            title=str(detail.get("title") or artwork_id),
            metadata={
                "gallery_id": artwork_id,
                "artwork_id": artwork_id,
                "artwork_type": int(detail.get("illustType", 0)),
                "author_id": str(detail.get("userId", "")),
                "author_name": str(detail.get("userName", "")),
                "create_date": str(detail.get("createDate", "")),
            },
            tags=_tags(detail),
        )

    async def list_assets(self, item: ResolvedItem) -> AssetList:
        artwork_id = str(item.metadata["artwork_id"])
        if item.metadata.get("artwork_type") == 2:
            metadata = await self._get_json(f"/ajax/illust/{artwork_id}/ugoira_meta")
            source = str(metadata.get("originalSrc") or metadata.get("src") or "")
            if not source:
                raise ValueError("Pixiv ugoira response does not contain a ZIP URL")
            return AssetList(
                assets=(
                    Asset(
                        url=source,
                        kind=AssetKind.FILE,
                        filename=_filename(source, f"{artwork_id}_ugoira.zip"),
                        metadata={
                            "asset_id": f"{artwork_id}:ugoira",
                            "artwork_id": artwork_id,
                            "frames": metadata.get("frames", []),
                            "referer": f"{_PIXIV_ROOT}/artworks/{artwork_id}",
                        },
                    ),
                )
            )
        pages = await self._get_json(f"/ajax/illust/{artwork_id}/pages")
        if not isinstance(pages, list):
            raise ValueError("Pixiv pages response is not a list")
        assets = tuple(
            Asset(
                url=str(page["urls"]["original"]),
                kind=AssetKind.IMAGE,
                filename=_filename(str(page["urls"]["original"]), f"{artwork_id}_p{index}"),
                metadata={
                    "asset_id": f"{artwork_id}:p{index}",
                    "artwork_id": artwork_id,
                    "index": index,
                    "width": page.get("width"),
                    "height": page.get("height"),
                    "referer": f"{_PIXIV_ROOT}/artworks/{artwork_id}",
                },
            )
            for index, page in enumerate(pages)
        )
        return AssetList(assets=assets)

    async def choose_strategy(self, item: ResolvedItem) -> DownloadStrategyPlan:
        return DownloadStrategyPlan(
            strategy=DownloadStrategy.DIRECT,
            reason="pixiv_original_assets",
            assets=await self.list_assets(item),
        )

    async def fetch(self, asset: Asset) -> bytes:
        referer = str(asset.metadata.get("referer") or _IMAGE_REFERER)
        return await self._get_bytes(asset.url, referer=referer)

    async def fetch_stream(self, asset: Asset) -> AsyncIterator[tuple[bytes, int | None]]:
        referer = str(asset.metadata.get("referer") or _IMAGE_REFERER)
        
        loop = asyncio.get_running_loop()
        headers = {"User-Agent": self._user_agent, "Referer": referer}
        cookie_header = (
            cookie_header_for_url(self._browser_session, asset.url) if self._browser_session else None
        )
        if cookie_header:
            headers["Cookie"] = cookie_header
        elif self._legacy_phpsessid and (urlparse(asset.url).hostname or "").endswith("pixiv.net"):
            headers["Cookie"] = f"PHPSESSID={self._legacy_phpsessid}"
            
        request = Request(asset.url, headers=headers)
        
        def _open_req():
            return urlopen(request, timeout=self._timeout)
            
        response = await loop.run_in_executor(None, _open_req)
        
        try:
            total_size_str = response.headers.get("Content-Length")
            total_size = int(total_size_str) if total_size_str and total_size_str.isdigit() else None
            
            while True:
                chunk = await loop.run_in_executor(None, response.read, 262144)
                if not chunk:
                    break
                yield chunk, total_size
        finally:
            await loop.run_in_executor(None, response.close)

    async def _artwork_result(self, request: OperationRequest) -> OperationResult:
        artwork_id = request.route.captures["artwork_id"]
        detail = await self._get_json(f"/ajax/illust/{artwork_id}")
        return OperationResult(
            request_id=request.request_id,
            result_kind=ResultKind.GALLERY,
            data=GalleryData(
                source_url=request.source_url,
                site_id=self.site_id,
                gallery_id=artwork_id,
                title=str(detail.get("title") or artwork_id),
                authors=(str(detail.get("userName", "Unknown")),),
                tags=_tags(detail),
                expected_asset_count=int(detail.get("pageCount", 1)),
                metadata={
                    "artwork_type": int(detail.get("illustType", 0)),
                    "author_id": str(detail.get("userId", "")),
                    "create_date": str(detail.get("createDate", "")),
                },
            ),
        )

    async def _user_result(self, request: OperationRequest) -> OperationResult:
        user_id = request.route.captures["user_id"]
        page_number = int(request.params.get("page", 1))
        page_size = int(request.params.get("page_size", 20))
        profile, all_work = await asyncio.gather(
            self._get_json(f"/ajax/user/{user_id}?full=1"),
            self._get_json(f"/ajax/user/{user_id}/profile/all"),
        )
        illusts = all_work.get("illusts") or {}
        manga = all_work.get("manga") or {}
        merged = {
            **(illusts if isinstance(illusts, Mapping) else {}),
            **(manga if isinstance(manga, Mapping) else {}),
        }
        artwork_ids = tuple(sorted(merged.keys(), key=lambda x: int(x), reverse=True))
        total_pages = max(1, ceil(len(artwork_ids) / page_size))
        if page_number > total_pages:
            raise ValueError(f"Pixiv user page exceeds {total_pages}")
        start = (page_number - 1) * page_size
        selected_ids = artwork_ids[start : start + page_size]
        works = await self._get_user_works(user_id, selected_ids)
        items = tuple(
            _list_item(works.get(artwork_id, {}), artwork_id) for artwork_id in selected_ids
        )
        title = f"{profile.get('name') or user_id} Illustrations"
        previous_action = _page_action("previous_page", page_number - 1, page_size)
        next_action = _page_action("next_page", page_number + 1, page_size)
        if page_number == 1:
            previous_action = None
        if page_number >= total_pages:
            next_action = None
        return OperationResult(
            request_id=request.request_id,
            result_kind=ResultKind.LIST_PAGE,
            data=ListPageData(
                title=title,
                items=items,
                page_info=PageInfo(
                    current_page=page_number,
                    page_size=page_size,
                    total_items=len(artwork_ids),
                    total_pages=total_pages,
                    previous_token=str(page_number - 1) if previous_action else None,
                    next_token=str(page_number + 1) if next_action else None,
                ),
            ),
            page=Page(
                header=(
                    Title(text=title),
                    Text(text=f"{len(artwork_ids)} works"),
                ),
                content=(
                    ListView(
                        widget_id="results",
                        items=tuple(
                            ListItem(
                                widget_id=item.item_id,
                                title=item.title,
                                text=item.summary,
                            )
                            for item in items
                        ),
                        selection_mode=SelectionMode.MULTIPLE,
                    ),
                    Pagination(
                        widget_id="pagination",
                        current_page=page_number,
                        total_pages=total_pages,
                        previous_action=previous_action,
                        next_action=next_action,
                    ),
                ),
                actions=(
                    Button(
                        widget_id="download_selected",
                        text="Download selected",
                        action=Action(
                            action_id="download_selected",
                            kind=ActionKind.DOWNLOAD,
                        ),
                    ),
                ),
            ),
            available_actions=tuple(
                action.action_id for action in (previous_action, next_action) if action is not None
            )
            + ("download_selected",),
        )

    async def _get_user_works(
        self,
        user_id: str,
        artwork_ids: tuple[str, ...],
    ) -> Mapping[str, object]:
        if not artwork_ids:
            return {}
        query = urlencode(
            [
                *(("ids[]", artwork_id) for artwork_id in artwork_ids),
                ("work_category", "illustManga"),
                ("is_first_page", "1"),
            ]
        )
        body = await self._get_json(f"/ajax/user/{user_id}/profile/illusts?{query}")
        works = body.get("works", {})
        return works if isinstance(works, Mapping) else {}

    async def _get_json(self, path: str) -> object:
        separator = "&" if "?" in path else "?"
        content = await self._get_bytes(
            f"{_PIXIV_ROOT}{path}{separator}lang={self._language}",
            referer=_IMAGE_REFERER,
        )
        payload = json.loads(content)
        if not isinstance(payload, dict) or payload.get("error"):
            message = (
                payload.get("message", "invalid response")
                if isinstance(payload, dict)
                else "invalid response"
            )
            raise ValueError(f"Pixiv request failed: {message}")
        return payload.get("body")

    async def _get_bytes(self, url: str, *, referer: str) -> bytes:
        def request_bytes() -> bytes:
            headers = {"User-Agent": self._user_agent, "Referer": referer}
            cookie_header = (
                cookie_header_for_url(self._browser_session, url) if self._browser_session else None
            )
            if cookie_header:
                headers["Cookie"] = cookie_header
            elif self._legacy_phpsessid and (urlparse(url).hostname or "").endswith("pixiv.net"):
                headers["Cookie"] = f"PHPSESSID={self._legacy_phpsessid}"
            request = Request(url, headers=headers)
            with urlopen(request, timeout=self._timeout) as response:
                return response.read()

        return await asyncio.to_thread(request_bytes)


def _tags(detail: Mapping[str, object]) -> tuple[str, ...]:
    tags = detail.get("tags", {})
    entries = tags.get("tags", []) if isinstance(tags, Mapping) else []
    return tuple(
        str(entry["tag"]) for entry in entries if isinstance(entry, Mapping) and entry.get("tag")
    )


def _filename(url: str, fallback: str) -> str:
    return PurePosixPath(urlparse(url).path).name or fallback


def _list_item(work: object, artwork_id: str) -> ListItemData:
    data = work if isinstance(work, Mapping) else {}
    thumbnail_url = str(data.get("url") or "")
    thumbnail = (
        AssetData(
            asset_id=f"{artwork_id}:thumbnail",
            url=thumbnail_url,
            headers={"Referer": _IMAGE_REFERER},
            referrer=_IMAGE_REFERER,
        )
        if thumbnail_url
        else None
    )
    page_count = int(data.get("pageCount", 1))
    return ListItemData(
        item_id=artwork_id,
        source_url=f"{_PIXIV_ROOT}/artworks/{artwork_id}",
        title=str(data.get("title") or f"Artwork {artwork_id}"),
        thumbnail=thumbnail,
        summary=f"{page_count} image{'s' if page_count != 1 else ''}",
        tags=tuple(str(tag) for tag in data.get("tags", []) if isinstance(tag, str)),
        metadata={
            "artwork_type": int(data.get("illustType", 0)),
            "page_count": page_count,
            "author_id": str(data.get("userId", "")),
            "author_name": str(data.get("userName", "")),
        },
    )


def _page_action(action_id: str, page: int, page_size: int) -> Action:
    return Action(
        action_id=action_id,
        kind=ActionKind.INVOKE_OPERATION,
        operation_id="user_illustrations",
        params={"page": page, "page_size": page_size},
    )
