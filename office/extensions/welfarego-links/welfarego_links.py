# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Welfarego OFFICE 실무 서식·계산기 바로가기 UNO ProtocolHandler.

- 오피스 실행·종료 시 자동 팝업이나 백그라운드 실행을 일절 수행하지 않습니다.
- 오직 사용자가 메뉴 또는 툴바 버튼을 직접 클릭했을 때만 OS 기본 웹브라우저로
  명시된 실무 도구·서식자료실(https://welfarego.co.kr/go/*)을 엽니다.
"""

import uno
import unohelper
from com.sun.star.frame import FeatureStateEvent, XDispatch, XDispatchProvider
from com.sun.star.lang import XInitialization

IMPL_NAME = "kr.co.welfarego.office.LinksProtocolHandler"
SERVICE_NAMES = ("com.sun.star.frame.ProtocolHandler",)
PROTOCOL_PREFIX = "kr.co.welfarego.links:"

# 허용된 목적지 화이트리스트 (명시된 https:// 주소만 열림)
ALLOWED_TARGETS = {
    "forms": "https://welfarego.co.kr/go/forms",
    "tools": "https://welfarego.co.kr/go/tools",
    "worktime": "https://welfarego.co.kr/go/worktime",
    "calendar": "https://welfarego.co.kr/go/calendar",
    "record": "https://welfarego.co.kr/go/record",
    "shuttle": "https://welfarego.co.kr/go/shuttle",
    "staffing": "https://welfarego.co.kr/go/staffing",
    "fees": "https://welfarego.co.kr/go/fees",
    "checklist": "https://welfarego.co.kr/go/checklist",
    "eval": "https://welfarego.co.kr/go/eval",
}

# com.sun.star.system.SystemShellExecuteFlags.URIS_ONLY == 1
URIS_ONLY_FLAG = 1


class WelfaregoLinksHandler(unohelper.Base, XDispatchProvider, XDispatch, XInitialization):
    def __init__(self, ctx):
        self.ctx = ctx
        self.frame = None

    def initialize(self, args):
        if args and len(args) > 0:
            self.frame = args[0]

    def queryDispatch(self, url, target_frame_name, search_flags):
        if url.Protocol == PROTOCOL_PREFIX and url.Path in ALLOWED_TARGETS:
            return self
        return None

    def queryDispatches(self, requests):
        return tuple(
            self.queryDispatch(req.FeatureURL, req.FrameName, req.SearchFlags)
            for req in requests
        )

    def dispatch(self, url, args):
        if url.Protocol != PROTOCOL_PREFIX:
            return
        target_url = ALLOWED_TARGETS.get(url.Path)
        if not target_url:
            return
        launcher = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.system.SystemShellExecute", self.ctx
        )
        launcher.execute(target_url, "", URIS_ONLY_FLAG)

    def addStatusListener(self, control, url):
        if not control:
            return
        ev = FeatureStateEvent()
        ev.Source = self
        ev.FeatureURL = url
        ev.IsEnabled = url.Path in ALLOWED_TARGETS
        ev.Requery = False
        control.statusChanged(ev)

    def removeStatusListener(self, control, url):
        pass


g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(
    WelfaregoLinksHandler,
    IMPL_NAME,
    SERVICE_NAMES,
)
