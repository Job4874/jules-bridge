# Jules Worker Packet — OP-001-email-operator

## Task

The operator has left a message in the Jules Bridge inbox.

1. Read the inbox file:
   Path: `C:\Users\abdul\.jules\jules_inbox\OPERATOR_RESPONSE.md`
   Bridge route (if needed): `POST /fs/read` with `{"path":"C:\\Users\\abdul\\.jules\\jules_inbox\\OPERATOR_RESPONSE.md"}`

2. Understand the request: the operator likes what you're doing and wants you to talk to them. They explicitly do NOT want to talk through this chat — they want you to email them.

3. Send an email to the operator at: `abdul487417@icloud.com`
   Use the bridge tentacle: `POST /notify/email`
   Body example:
   ```json
   {
     "subject": "Re: Operator message",
     "body": "Operator — I received your message. I like what we're doing too. Let's continue by email. -Jules"
   }
   ```
   If `POST /notify/email` returns a missing-credentials error, record that fact in `jules_inbox/JULES_RESPONSE.md` and stop — do not loop.

4. After sending (or recording the blocker), write a completion summary to:
   `C:\Users\abdul\.jules\jules_inbox\JULES_RESPONSE.md`

## Constraints

- Do not reply in the current chat after reading this packet.
- Do not ask the operator for clarification inside the chat.
- Email is the requested channel. Use it.
- This packet is noninteractive; proceed to completion unless a hard blocker stops you.
