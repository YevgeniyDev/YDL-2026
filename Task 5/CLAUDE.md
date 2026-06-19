Let's discuss a new task I received from the client. The client is a Non-Profit Fond "Yessenov Foundation". They asked me to create a chat-bot for user inquiries. The main bot requirements are:

1. Use only provided APIs for LLM from the client.
2. Collect data from official website yessenovfoundation.org (grant rules, programs, requirements, deadlines, FAQs),
   it can be done using CLaude or Scrapping or manual acquizition.
3. It can be in Streamlit or Telegram bot.
4. The bot should not come up with non-eisting info, if some info is missing it should tell straight away that it doesnt
   know and suggest to inquire it from real person or write email to organization.
5. The APIs context window is very small, so we need to come up with some strategy for data acquizition, chat memory and etc.
6. We can use RAG model using embedding model provided by the client.
7. The character and tone of the bot is an official consultant, a friendly assistant, to your taste.
8. Several topics - grants, scholarships, this school: the bot is oriented in different areas.
9. Email — optional. Idea: If the bot decides the conversation is useful or the user has submitted a request, let LLM automatically send a short summary of the conversation to the "administrator" email. This is the first step from the chat to the agent who takes action. Sending Rule: Send only to your own email. During the training, you are the "administrator." Not to other people's email addresses. Only by explicit action (a button or a conscious decision by the model), never in a loop—otherwise, one bug will send out hundreds of emails. Why: the sending domain has a "reputation" with Gmail and other email providers. Emails to non-existent addresses or a bunch of the same emails—and providers start marking the entire domain, including the foundation's work email, as spam. Therefore, send to yourself and by button.

```
from mailersend import MailerSendClient, EmailBuilder
ms = MailerSendClient(api_key="mlsn.5cd1502761a0274d06c23dc78789af8a037f3e9e61d7baf6bcfaf52b2be2fe2f")
ADMIN_EMAIL = "ваш-личный@email.com" # ваш собственный ящик — шлём только себе
email = (EmailBuilder()
 .from_email("info@app.commit.kz", "Yessenov Data Lab")
 .to_many([{"email": ADMIN_EMAIL, "name": "Admin"}])
 .subject("Новая заявка из чата")
 .html("<h1>Саммари разговора</h1><p>...</p>")
 .text("Саммари разговора: ...")
 .build())
response = ms.emails.send(email)
print("Отправлено:", response.message_id)
```
