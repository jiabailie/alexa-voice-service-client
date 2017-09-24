from avs_client import AlexaVoiceServiceClient
import threading
import sys

ipath = sys.argv[1]
opath = sys.argv[2]

print(ipath)
print(opath)

alexa_client = AlexaVoiceServiceClient(
    client_id='client_id',
    secret='secret',
    refresh_token='refresh_token',
)

# def ping_avs():
#     while True:
#         alexa_client.conditional_ping()
#
# ping_thread = threading.Thread(target=ping_avs)
# ping_thread.start()

alexa_client.connect()  # authenticate and other handshaking steps
with open(ipath, 'rb') as f:
    alexa_response_audio = alexa_client.send_audio_file(f)
with open(opath, 'wb') as f:
    f.write(alexa_response_audio)
