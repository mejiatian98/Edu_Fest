from twilio.rest import Client
from django.conf import settings

def enviar_sms(numero_destino, mensaje):
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        # Asegurar que el número tenga formato internacional (por defecto +57 Colombia)
        if not numero_destino.startswith("+"):
            numero_destino = "+57" + numero_destino.strip().lstrip("0")

        message = client.messages.create(
            body=mensaje,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=numero_destino
        )
        return True, message.sid
    except Exception as e:
        return False, str(e)
