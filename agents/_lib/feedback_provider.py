class HumanFeedbackPending(Exception):
    """Flow 暂停等待人工反馈"""

    def __init__(self, context=None):
        self.context = context
        super().__init__("Human feedback pending")


class PagesAsyncProvider:
    """
    Pages 平台的异步反馈提供者。
    调用 request_feedback 时抛出 HumanFeedbackPending 暂停 Flow，
    由 stream.py 捕获后返回 SSE 给前端，等待下次请求 resume。
    """

    def request_feedback(self, context, flow):
        raise HumanFeedbackPending(context=context)
