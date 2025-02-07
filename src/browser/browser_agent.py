import asyncio
import logging
import os
from typing import Optional

from botbuilder.core import TurnContext
from botbuilder.schema import Activity, Attachment, AttachmentLayoutTypes
from browser_use import Agent, Browser
from browser_use.agent.views import AgentHistoryList, AgentOutput
from browser_use.browser.context import BrowserContext
from browser_use.browser.views import BrowserState
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from browser.session import SessionStepState


class BrowserAgent:
    def __init__(self, context: TurnContext, activity_id: str):
        self.context = context
        self.activity_id = activity_id
        self.browser = Browser()
        self.browser_context = BrowserContext(browser=self.browser)
        self.llm = self._setup_llm()

    @staticmethod
    def _setup_llm():
        if azure_endpoint := os.environ.get("AZURE_OPENAI_API_BASE", None):
            return AzureChatOpenAI(
                azure_endpoint=azure_endpoint,
                azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
                openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
                model_name=os.environ[
                    "AZURE_OPENAI_DEPLOYMENT"
                ],  # BrowserUse has a bug where this model_name is required
            )
        return ChatOpenAI(model=os.environ["OPENAI_MODEL_NAME"])

    def _create_progress_card(
        self,
        action: str,
        next_goal: str = None,
        final_result: str = None,
        screenshot: str = None,
        agent_history: AgentHistoryList = None,
    ) -> dict:
        card = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.5",
            "body": [],
        }

        # Add screenshot if available
        if screenshot:
            card["body"].append(
                {"type": "Image", "url": f"data:image/png;base64,{screenshot}"}
            )

        # Add progress section with next goal
        if next_goal:
            progress_section = {
                "type": "ColumnSet",
                "columns": [
                    {
                        "type": "Column",
                        "width": "auto",
                        "items": [{"type": "TextBlock", "text": "🎯", "wrap": True}],
                    },
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": (
                                    next_goal if next_goal else "Task in progress..."
                                ),
                                "wrap": True,
                            }
                        ],
                    },
                ],
            }
            card["body"].append(progress_section)

        # Add action/result section
        status_section = {
            "type": "ColumnSet",
            "columns": [
                {
                    "type": "Column",
                    "width": "auto",
                    "items": [{"type": "TextBlock", "text": "⚡", "wrap": True}],
                },
                {
                    "type": "Column",
                    "width": "stretch",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": final_result if final_result else action,
                            "wrap": True,
                        }
                    ],
                },
            ],
        }
        card["body"].append(status_section)

        # Add history toggle and fact set if history exists
        if agent_history and agent_history.history:
            # Get all model thoughts and actions
            thoughts = agent_history.model_thoughts()
            actions = agent_history.model_actions()

            facts = []
            for i, (thought, action) in enumerate(zip(thoughts, actions)):
                action_name = list(action.keys())[0] if action else "No action"
                facts.append(
                    {
                        "title": f"Step {i+1}",
                        "value": f"🤔 Thought: {thought.evaluation_previous_goal}\n"
                        f"🎯 Goal: {thought.next_goal}\n"
                        f"⚡ Action: {action_name}",
                    }
                )

            card["body"].extend(
                [
                    {
                        "type": "ActionSet",
                        "actions": [
                            {
                                "type": "Action.ToggleVisibility",
                                "title": "📝 Show History",
                                "targetElements": ["history_facts"],
                            }
                        ],
                    },
                    {
                        "type": "FactSet",
                        "id": "history_facts",
                        "isVisible": False,
                        "facts": facts,
                    },
                ]
            )

        return card

    async def _handle_screenshot_and_emit(
        self, step: SessionStepState, io: Optional[object]
    ) -> None:
        screenshot_new = await self.browser_context.take_screenshot()
        step.screenshot = screenshot_new

        if session := self.context.get("session"):
            session.session_state.append(step)

            # Update the Teams message with card
            activity = Activity(
                id=self.activity_id,
                type="message",
                attachment_layout=AttachmentLayoutTypes.list,
                attachments=[
                    Attachment(
                        content_type="application/vnd.microsoft.card.adaptive",
                        content=self._create_progress_card(
                            action=step.action,
                            next_goal=step.next_goal,
                            screenshot=step.screenshot,
                            agent_history=self.agent_history,
                        ),
                    )
                ],
            )
            await self.context.update_activity(activity=activity)

            # Emit to socket if available
            if io:
                await io.emit(
                    "message",
                    {
                        "screenshot": step.screenshot,
                        "action": step.action,
                        "memory": step.memory,
                        "next_goal": step.next_goal,
                        "actions": step.actions,
                    },
                )

    def step_callback(
        self, state: BrowserState, output: AgentOutput, step_number: int
    ) -> None:
        if session := self.context.get("session"):
            actions = (
                [action.model_dump_json(exclude_unset=True) for action in output.action]
                if output.action
                else []
            )

            step = SessionStepState(
                screenshot=None,
                action=output.current_state.evaluation_previous_goal,
                memory=output.current_state.memory,
                next_goal=output.current_state.next_goal,
                actions=actions,
            )

            # Handle screenshot and update card in one go
            asyncio.create_task(
                self._handle_screenshot_and_emit(step, self.context.get("socket"))
            )
        else:
            logging.warning("Session not available to store step state")

    async def run(self, query: str) -> str:
        agent = Agent(
            task=query,
            llm=self.llm,
            register_new_step_callback=self.step_callback,
            browser_context=self.browser_context,
            generate_gif=False,
        )
        self.agent_history = agent.history

        try:
            result = await agent.run()
            asyncio.create_task(self.browser_context.close())

            action_results = result.action_results()
            if action_results and (last_result := action_results[-1]):
                final_result = last_result.extracted_content
                # Final update with completion status
                activity = Activity(
                    id=self.activity_id,
                    type="message",
                    attachment_layout=AttachmentLayoutTypes.list,
                    attachments=[
                        Attachment(
                            content_type="application/vnd.microsoft.card.adaptive",
                            content=self._create_progress_card(
                                action="Task completed",
                                final_result=final_result,
                            ),
                        )
                    ],
                )
                await self.context.update_activity(activity=activity)
                return final_result
            else:
                # No results case
                activity = Activity(
                    id=self.activity_id,
                    type="message",
                    attachment_layout=AttachmentLayoutTypes.list,
                    attachments=[
                        Attachment(
                            content_type="application/vnd.microsoft.card.adaptive",
                            content=self._create_progress_card(
                                action="Task completed",
                                final_result="No results found",
                            ),
                        )
                    ],
                )
                await self.context.update_activity(activity=activity)
                return "No results found"

        except Exception as e:
            error_message = f"Error during browser agent execution: {str(e)}"
            activity = Activity(
                id=self.activity_id,
                type="message",
                attachment_layout=AttachmentLayoutTypes.list,
                attachments=[
                    Attachment(
                        content_type="application/vnd.microsoft.card.adaptive",
                        content=self._create_progress_card(
                            action="Error occurred",
                            final_result=error_message,
                        ),
                    )
                ],
            )
            await self.context.update_activity(activity=activity)
            return error_message
