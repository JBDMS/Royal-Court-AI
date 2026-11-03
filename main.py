from app.chatbot import ask_ai
from app.utils import print_title


def main():

    print_title()

    while True:

        question = input("\nYou : ")

        if question.lower() == "exit":
            print("\nGoodbye!")
            break

        answer = ask_ai(question)

        print("\nAI :", answer)


if __name__ == "__main__":
    main()