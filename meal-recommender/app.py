"""Gradio Web UI - 大学生吃什么推荐系统"""

import gradio as gr
from agent.agent import MealRecommenderAgent


SYSTEM_WELCOME = """你好！不知道吃什么？我来帮你～

直接告诉我你想吃什么类型的就行，比如：
- "想吃辣的，30 块左右"
- "随便吃，清淡点"
- "今天心情不好，想吃点好的"

告诉我你的想法吧！」"""


def create_agent() -> MealRecommenderAgent:
    """创建 Agent 实例"""
    return MealRecommenderAgent()


def init_chat(agent: MealRecommenderAgent) -> list:
    """初始化聊天
    
    Args:
        agent: Agent 实例
        
    Returns:
        list: 初始聊天历史
    """
    return [[None, SYSTEM_WELCOME]]


def chat_respond(
    message: str,
    history: list,
    agent: MealRecommenderAgent,
) -> tuple:
    """处理聊天消息
    
    Args:
        message: 用户输入
        history: 聊天历史
        agent: Agent 实例
        
    Returns:
        tuple: (更新后的历史, 空输入框)
    """
    if not message or not message.strip():
        return history, ""
    
    response = agent.invoke(message)
    history.append([message, response])
    
    return history, ""


def reset_chat(agent: MealRecommenderAgent) -> list:
    """重置聊天
    
    Args:
        agent: Agent 实例
        
    Returns:
        list: 新的聊天历史
    """
    agent.reset()
    return init_chat(agent)


def create_interface() -> gr.Blocks:
    """创建 Gradio 聊天界面
    
    Returns:
        gr.Blocks: Gradio 界面
    """
    with gr.Blocks(title="吃什么推荐助手") as interface:
        gr.Markdown("""
        # 吃什么推荐助手
        不知道吃什么？简单聊几句，帮你挑顿合胃口的！
        """)
        
        # 每会话独立 Agent
        agent_state = gr.State(create_agent)
        
        chatbot = gr.Chatbot(
            height=500,
            label="对话",
        )
        
        with gr.Row():
            message_input = gr.Textbox(
                placeholder="输入你的想法...（例如：想吃清淡的，预算 20 左右）",
                show_label=False,
                container=False,
            )
            send_btn = gr.Button("发送", variant="primary")
            reset_btn = gr.Button("重新开始", variant="secondary")
        
        # 发送
        send_btn.click(
            fn=chat_respond,
            inputs=[message_input, chatbot, agent_state],
            outputs=[chatbot, message_input],
        )
        
        # 重置
        reset_btn.click(
            fn=reset_chat,
            inputs=[agent_state],
            outputs=[chatbot],
        )
        
        # 回车发送
        message_input.submit(
            fn=chat_respond,
            inputs=[message_input, chatbot, agent_state],
            outputs=[chatbot, message_input],
        )
        
        # 初始加载
        interface.load(
            fn=init_chat,
            inputs=[agent_state],
            outputs=[chatbot],
        )
    
    return interface


if __name__ == "__main__":
    app = create_interface()
    app.queue()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
    )
