from api.abstract_request_command import AbstractRequestCommand


class HelloCommand(AbstractRequestCommand):
    NAME = "hello"
    LABEL = "Say Hello"

    async def run(self) -> str:
        return "Hello from {{BOT_NAME}}! The bot is running."
