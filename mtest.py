from avs_client import AlexaVoiceServiceClient
import threading

alexa_client = AlexaVoiceServiceClient(
    client_id='',
    secret='',
    refresh_token='',
)

# def ping_avs():
#     while True:
#         alexa_client.conditional_ping()
#
# ping_thread = threading.Thread(target=ping_avs)
# ping_thread.start()

alexa_client.connect()  # authenticate and other handshaking steps
with open('./tests/resources/alexa_what_time_is_it.wav', 'rb') as f:
    alexa_response_audio = alexa_client.send_audio_file(f)
with open('./output.wav', 'wb') as f:
    f.write(alexa_response_audio)
