# SGM Keys Updater V2.1 — visualização de progresso

Esta atualização mantém o fluxo V2 que funcionou no OLED, acrescentando **sete marcos de progresso reais** (operações concluídas, não porcentagens por tempo), etapa atual e tempo decorrido registrado nos pontos de atualização. O processamento de tickets utiliza a barra existente do Lockpick. O intervalo de processamento interno de saves pode continuar sem atualizações visuais; a interface avisa que pode durar alguns minutos. **Não existe spinner ininterrupto na V2.1**: exigir isso requer instrumentar loops do mecanismo de leitura de saves de forma segura.

## Publicar no GitHub

Substitua no repositório existente os arquivos `apply_sgm.py`, `.github/workflows/build-sgm.yml`, `README.md` e os testes nesta pasta. Publique na branch `main`, sem incluir arquivos de chave. O GitHub Actions fará a compilação e disponibilizará `SGM_Keys_Updater.bin` e o ZIP Hekate como artefatos `SGM-Keys-Updater-V2.1`.

## Segurança

O firmware deve permanecer no ambiente oficial de testes enquanto a V2.1 não for validada. O projeto não inclui chaves reais; o processo gera arquivos somente no SD local. Faça backup prévio de `prod.keys` e `keys.txt`.

## Fonte

Aplica o patch em `THZoria/Lockpick_RCMaster`, tag `2.0.1` e commit fixado no workflow. GPLv2, preservando a atribuição ao projeto original.
