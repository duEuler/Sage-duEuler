# Push da família duEuler

O PWA usa Firebase Auth anônimo e grava somente o token FCM da inscrição no Firestore. O service worker recebe mensagens de dados do FCM. O Pages hospeda a interface. O GitHub Actions envia a edição aprovada depois do deploy.

## Ativação no projeto lutandopelahumanidade

1. Use uma conta autorizada no Google Cloud deste projeto. Confirme Firebase Auth anônimo, Firestore e as APIs Firebase Cloud Messaging e FCM Registration. Em Firebase → Configurações do projeto → Cloud Messaging → Certificados Web Push, gere ou informe o par do projeto. Coloque somente a **chave pública** em docs/push-config.js.
2. Leia as regras Firestore vigentes antes de aplicar qualquer atualização. Adicione o bloco de firestore-sage-push.match.rules ao match de documentos e confira se alguma regra mais ampla permite leituras, listagens ou escritas nas três coleções do PWA. Preserve as autorizações das demais coleções. As coleções de recibos e campanhas ficam restritas ao IAM.
3. Vincule GitHub Actions ao Google Cloud com Workload Identity Federation, limitada ao repositório duEuler/Sage-duEuler e à ref refs/heads/main. A conta de serviço emissora precisa gravar e consultar as coleções Firestore e enviar pela API do FCM. Os papéis padrão são Cloud Datastore User e Firebase Cloud Messaging API Admin. A federação usa credenciais temporárias do Google.
4. Configure no GitHub as variáveis FIREBASE_PUSH_IDENTITY_PROVIDER e FIREBASE_PUSH_SERVICE_ACCOUNT. Só habilite FIREBASE_PUSH_ENABLED=true após verificar as regras e publicar a chave pública VAPID.
5. No PWA, ative o push num dispositivo de teste. Faça uma publicação com novo ID em docs/atualizacoes.json. Confira a entrega com a aba fechada e depois a desinscrição. No iOS compatível, instale o PWA na tela de início antes de pedir permissão.

O ID da edição deve conter apenas letras minúsculas, números e hífens. Mude o ID ao publicar uma nova história ou atualização no site. O job reaproveita recibos de envios aceitos e pula edições encerradas. O registro do envio mede aceitação pelo FCM. A entrega e exibição dependem do navegador e do dispositivo.

[FCM para Web](https://firebase.google.com/docs/cloud-messaging/web/get-started) · [FCM HTTP v1](https://firebase.google.com/docs/cloud-messaging/send/v1-api) · [Federação para pipelines](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)
