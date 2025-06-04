🎙️ Guia: Utilizando a API de Transcrição de Fala da ElevenLabs
A API de transcrição de fala da ElevenLabs permite converter arquivos de áudio ou vídeo em texto com alta precisão, fornecendo timestamps por palavra, identificação de falantes e detecção de eventos sonoros.

🔑 Autenticação
Para acessar a API, é necessário incluir sua chave de API no cabeçalho da requisição:

http
Copiar
Editar
xi-api-key: <sua_chave_de_api>
Você pode obter sua chave de API no painel da ElevenLabs em: Configurações de API

📤 Endpoint de Transcrição
URL:

bash
Copiar
Editar

POST https://api.elevenlabs.io/v1/speech-to-text
Cabeçalhos:

http
Copiar
Editar
Content-Type: multipart/form-data
xi-api-key: <sua_chave_de_api>
Parâmetros do Formulário:

model_id (obrigatório): ID do modelo de transcrição a ser utilizado. Atualmente, os modelos disponíveis são:

scribe_v1

scribe_v1_experimental

file (opcional): Arquivo de áudio ou vídeo a ser transcrito. Todos os principais formatos são suportados. O tamanho máximo do arquivo é de 1GB.

cloud_storage_url (opcional): URL de um arquivo armazenado em serviços como AWS S3, Cloudflare R2 ou Google Cloud Storage. O arquivo deve ser publicamente acessível e ter no máximo 2GB.

language_code (opcional): Código ISO-639-1 ou ISO-639-3 correspondente ao idioma do áudio. Se não fornecido, o idioma será detectado automaticamente.

tag_audio_events (opcional): Booleano que indica se eventos sonoros como risos ou aplausos devem ser identificados. Padrão: true.

num_speakers (opcional): Número máximo de falantes no arquivo. Pode ajudar na identificação de quem está falando. Valor entre 1 e 32.

timestamps_granularity (opcional): Define a granularidade dos timestamps na transcrição. Valores possíveis:

word (padrão): timestamps por palavra

character: timestamps por caractere

diarize (opcional): Booleano que indica se a identificação de falantes deve ser realizada. Padrão: false.

file_format (opcional): Formato do áudio de entrada. Valores possíveis:

pcm_s16le_16: áudio PCM de 16 bits, 16kHz, mono, little-endian

other (padrão): outros formatos

webhook (opcional): Booleano que indica se a requisição deve ser processada de forma assíncrona, com os resultados enviados para webhooks configurados. Padrão: false.
elevenlabs.io
+2
blog.addpipe.com
+2
elevenlabs.io
+2
elevenlabs.io
+1
blog.addpipe.com
+1

Nota: Exatamente um dos parâmetros file ou cloud_storage_url deve ser fornecido.
elevenlabs.io
+1
blog.addpipe.com
+1

📥 Exemplo de Requisição com cURL
bash
Copiar
Editar
curl -X POST https://api.elevenlabs.io/v1/speech-to-text \
  -H "xi-api-key: <sua_chave_de_api>" \
  -H "Content-Type: multipart/form-data" \
  -F model_id="scribe_v1" \
  -F file=@/caminho/para/seu_arquivo.mp3
📄 Exemplo de Resposta
json
Copiar
Editar
{
  "language_code": "en",
  "language_probability": 0.98,
  "text": "Hello world!",
  "words": [
    {
      "text": "Hello",
      "type": "word",
      "logprob": 42,
      "start": 0.0,
      "end": 0.5,
      "speaker_id": "speaker_1"
    },
    {
      "text": " ",
      "type": "spacing",
      "logprob": 42,
      "start": 0.5,
      "end": 0.5,
      "speaker_id": "speaker_1"
    },
    {
      "text": "world!",
      "type": "word",
      "logprob": 42,
      "start": 0.5,
      "end": 1.2,
      "speaker_id": "speaker_1"
    }
  ]
}
Campos da Resposta:

language_code: Código do idioma detectado.

language_probability: Probabilidade associada à detecção do idioma.

text: Texto completo transcrito.

words: Lista de objetos representando cada palavra ou espaço na transcrição, incluindo:

text: Texto da palavra ou espaço.

type: Tipo do elemento (word ou spacing).

logprob: Logaritmo da probabilidade associada à palavra.

start: Tempo de início da palavra no áudio (em segundos).

end: Tempo de término da palavra no áudio (em segundos).

speaker_id: Identificador do falante associado à palavra.

📝 Observações Adicionais
Modelos Disponíveis: Atualmente, os modelos de transcrição disponíveis são scribe_v1 e scribe_v1_experimental.

Tamanhos de Arquivo: Arquivos enviados diretamente devem ter no máximo 1GB. Para URLs de armazenamento em nuvem, o limite é de 2GB.

Eventos Sonoros: Se tag_audio_events estiver ativado, eventos como risos ou aplausos serão identificados na transcrição.

Identificação de Falantes: Ativar diarize permite que a transcrição identifique diferentes falantes no áudio.