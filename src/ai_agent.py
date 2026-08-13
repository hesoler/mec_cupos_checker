from groq import Groq
import logging


def consultar_agente_ia_groq(pregunta: str, agent_model) -> str:
    try:
        client = Groq()
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Eres un asistente que responde preguntas de seguridad de forma natural y precisa. En la mayoría de los casos la pregunta tiene una respuesta numérica tras realizar un simple cálculo matemático. Responde solo con la respuesta directa, sin explicaciones adicionales."
                },
                {
                    "role": "user",
                    "content": pregunta,
                },
            ],
            max_tokens=50,  # Limita la respuesta para evitar texto largo
            temperature=0.7,

            # The language model which will generate the completion.
            model=agent_model
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logging.error(f"Error al consultar agente IA: {e}")
        raise
