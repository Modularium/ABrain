from core.agents import AgentRuntime

def main():
    runtime = AgentRuntime()

    user_message = "Hallo, bitte finde alle Kunden mit offenen Rechnungen."
    response = runtime.handle_user_message_sync(user_message)
    print("Chatbot Antwort:", response)

if __name__ == "__main__":
    main()
