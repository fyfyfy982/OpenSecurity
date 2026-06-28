"""summary: hCaptcha 本地 ONNX 自动解决工具

description:
   基于 hcaptcha-challenger 0.10.1.post2 的本地 ONNX 推理管线，
   封装现代 hCaptcha 的兼容修复（HSW 解码、msgpack 二进制响应、
   iframe 选择器更新、QuestionResp 类型兼容、CSP 绕过）。

   核心能力：
   1. HSW 脚本注入 + msgpack 二进制响应解码
   2. 本地 ONNX 推理（ResNet 二分类 + YOLO 区域检测 + CLIP 零样本）
   3. 现代 iframe 选择器兼容
   4. 自动刷新 + retry（跳过不支持的 challenge 类型）
   5. 模型按需下载

   不依赖任何远程视觉 API（Gemini/OpenAI/Claude），完全本地推理。

    依赖: hcaptcha-challenger==0.10.1.post2 (--no-deps 安装),
          onnxruntime, opencv-python, scikit-learn, scikit-image,
          msgpack, ftfy, regex, pyyaml, importlib_metadata

   调用方式:
     import sys
     sys.path.insert(0, "$AGENT_DIR/scripts")
     from hcaptcha_solver import HCaptchaSolver

     solver = HCaptchaSolver(max_attempts=10)
     result = await solver.solve(page=page)

usage:
   CLI: $PYTHON_CMD $AGENT_DIR/scripts/hcaptcha_solver.py --url <URL> [--max-attempts N]

level: intermediate
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import msgpack
from hcaptcha_challenger.agents.playwright.control import AgentT
from hcaptcha_challenger.components.middleware import (
    ChallengeResp,
    QuestionResp,
    Status,
)
from hcaptcha_challenger.onnx.modelhub import ModelHub
from loguru import logger
from playwright.async_api import Page, async_playwright


# ── 兼容修复 ──

# 修复 1: iframe 选择器（旧版用 @title，现代 hCaptcha 用 @src）
_AGENT_HOOK_CHALLENGE = (
    "//iframe[contains(@src, 'hcaptcha') and contains(@src, 'frame=challenge')]"
)
_CHECKBOX_SELECTOR = "iframe[src*='hcaptcha'][src*='checkbox']"


def _ensure_objects_yaml():
    """恢复 objects.yaml（GitHub main 分支已删除，从历史提交恢复）。"""
    mh = ModelHub.from_github_repo()
    if mh.objects_path.exists() and mh.objects_path.stat().st_size > 100:
        return
    import urllib.request

    url = (
        "https://raw.githubusercontent.com/QIN2DIM/hcaptcha-challenger/"
        "5dbc4481cf9f/src/objects.yaml"
    )
    try:
        urllib.request.urlretrieve(url, mh.objects_path)
        logger.info("objects.yaml 已从 GitHub 历史提交恢复")
    except Exception as e:
        logger.error(f"恢复 objects.yaml 失败: {e}")
        logger.error(
            "手动恢复: curl -o "
            f"{mh.objects_path} "
            "https://raw.githubusercontent.com/QIN2DIM/hcaptcha-challenger/"
            "5dbc4481cf9f/src/objects.yaml"
        )


def _patch_question_resp():
    """QuestionResp.requester_question_example 类型兼容。

    现代 hCaptcha 返回 string，旧版期望 list。
    实际兼容处理在 _patch_handler 的 patched_handler 中完成
    （line: if isinstance(rqe, str): data["requester_question_example"] = [rqe]）。
    此函数保留为占位，确保兼容逻辑有明确入口。
    """
    pass


class HCaptchaSolver:
    """hCaptcha 本地 ONNX 自动解决器。

    使用 hcaptcha-challenger 0.10.1.post2 的本地推理管线，
    通过 monkey-patch 修复与现代 hCaptcha 的兼容性问题。
    """

    def __init__(
        self,
        max_attempts: int = 10,
        headless: bool = False,
        bypass_csp: bool = True,
    ):
        self.max_attempts = max_attempts
        self.headless = headless
        self.bypass_csp = bypass_csp

        # 初始化 ModelHub
        _ensure_objects_yaml()
        self.modelhub = ModelHub.from_github_repo()
        self.modelhub.parse_objects()

        # 修复兼容性
        _patch_question_resp()
        AgentT.HOOK_CHALLENGE = _AGENT_HOOK_CHALLENGE

    def _create_agent(self, page: Page) -> AgentT:
        """创建 AgentT 实例并注入兼容修复。"""
        agent = AgentT.from_page(page, modelhub=self.modelhub)
        agent.qr_queue = asyncio.Queue()
        agent.cr_queue = asyncio.Queue()
        return agent

    async def _patch_handler(self, page: Page, agent: AgentT):
        """替换原版 handler 为兼容现代 hCaptcha 的版本。

        处理：
        1. HSW 脚本注入
        2. msgpack 二进制响应解码
        3. QuestionResp 类型兼容
        4. 移除原版 handler 避免干扰
        """
        # 移除原版 handler（AgentT.__init__ 自动注册的）
        try:
            page.remove_listener("response", agent.handler)
        except Exception:
            pass

        async def patched_handler(response):
            url = response.url
            if url.endswith("/hsw.js"):
                try:
                    await page.evaluate(await response.text())
                except Exception:
                    pass
            elif "api.hcaptcha.com/getcaptcha/" in url:
                try:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        data = await response.json()
                    else:
                        raw = await response.body()
                        result = await page.evaluate(
                            f"async () => {{ const ba = new Uint8Array({list(raw)}); "
                            f"return Array.from(await hsw(0, ba)); }}"
                        )
                        data = msgpack.unpackb(bytes(result))

                    if data.get("pass"):
                        agent.cr_queue.put_nowait(ChallengeResp(**data))
                    else:
                        # 兼容 requester_question_example 为 string 的情况
                        rqe = data.get("requester_question_example")
                        if isinstance(rqe, str):
                            data["requester_question_example"] = [rqe]
                        agent.qr_queue.put_nowait(QuestionResp(**data))
                except Exception as e:
                    logger.debug(f"getcaptcha 解析失败: {type(e).__name__}: {e}")
            elif "api.hcaptcha.com/checkcaptcha/" in url:
                try:
                    agent.cr_queue.put_nowait(
                        ChallengeResp(**(await response.json()))
                    )
                except Exception:
                    pass

        page.on("response", patched_handler)

    async def solve(self, page: Page, sitekey: Optional[str] = None) -> dict:
        """在给定 Playwright page 上解决 hCaptcha。

        Args:
            page: Playwright Page 对象（已导航到含 hCaptcha 的页面）
            sitekey: hCaptcha sitekey（可选，默认自动检测）

        Returns:
            {"success": bool, "token": str, "attempts": int, "last_status": str, "error": str}
        """
        agent = self._create_agent(page)
        await self._patch_handler(page, agent)

        for attempt in range(1, self.max_attempts + 1):
            # 点击 checkbox
            try:
                checkbox = page.frame_locator(_CHECKBOX_SELECTOR)
                await checkbox.locator("#checkbox").click()
            except Exception:
                pass

            await page.wait_for_timeout(5000)

            # 检查直接通过
            if agent.cr_queue.qsize() > 0:
                token = await self._get_token(page)
                if token:
                    return {
                        "success": True,
                        "token": token,
                        "attempts": attempt,
                        "last_status": "DIRECT_PASS",
                    }

            # 尝试解决 challenge
            if agent.qr_queue.qsize() > 0:
                try:
                    status = await agent.execute()
                    if status == Status.CHALLENGE_SUCCESS:
                        await page.wait_for_timeout(2000)
                        token = await self._get_token(page)
                        if token:
                            return {
                                "success": True,
                                "token": token,
                                "attempts": attempt,
                                "last_status": status.name,
                            }
                except Exception as e:
                    logger.debug(f"attempt {attempt}: {type(e).__name__}: {e}")

            # 刷新重试
            while not agent.qr_queue.empty():
                agent.qr_queue.get_nowait()
            while not agent.cr_queue.empty():
                agent.cr_queue.get_nowait()
            try:
                refresh = page.frame_locator(AgentT.HOOK_CHALLENGE).locator(
                    "//div[@class='refresh button']"
                )
                await refresh.click()
            except Exception:
                pass
            await page.wait_for_timeout(3000)

        return {
            "success": False,
            "token": "",
            "attempts": self.max_attempts,
            "last_status": "MAX_ATTEMPTS",
            "error": f"Failed after {self.max_attempts} attempts",
        }

    async def _get_token(self, page: Page) -> str:
        """提取 h-captcha-response token。"""
        return await page.evaluate("""() => {
            const e = document.querySelector('[name="h-captcha-response"]');
            return (e && e.value && e.value.length > 10) ? e.value : '';
        }""")


async def _cli():
    """CLI 入口：$PYTHON_CMD hcaptcha_solver.py --url <URL>"""
    parser = argparse.ArgumentParser(
        description="hCaptcha 本地 ONNX 自动解决工具"
    )
    parser.add_argument("--url", required=True, help="目标页面 URL")
    parser.add_argument("--max-attempts", type=int, default=10, help="最大尝试次数")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--output", help="JSON 输出路径（默认 stdout）")
    args = parser.parse_args()

    solver = HCaptchaSolver(
        max_attempts=args.max_attempts,
        headless=args.headless,
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=args.headless)
        context = await browser.new_context(bypass_csp=solver.bypass_csp)
        page = await context.new_page()

        await page.goto(args.url, timeout=60000)
        await page.wait_for_timeout(3000)

        result = await solver.solve(page)

        await browser.close()

    output = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    asyncio.run(_cli())
