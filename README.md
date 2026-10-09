# SGM Keys Updater 2.0 — BuildKit para Hekate

**Status:** fonte da modificação pronta, compilação automatizada preparada; **nenhum BIN está incluído**. Não foi testado em Switch.

**Base:** [THZoria/Lockpick_RCMaster](https://github.com/THZoria/Lockpick_RCMaster) v2.0.1, com suporte a chaves do HOS 23.0.0 (conforme release pública de setembro/2026). Modificação GPLv2.

## Como obter o payload sem instalar devkitARM no Windows

1. No repositório [`SGMSteeL1/sgm-keys-updater`](https://github.com/SGMSteeL1/sgm-keys-updater), envie todo o conteúdo desta pasta, **incluindo `.github/workflows/build-sgm.yml`**.
2. Abra **Actions → Build SGM Keys Updater → Run workflow** (ou aguarde a execução pelo push).
3. Se a compilação terminar com sucesso, abra a execução e baixe o artifact `SGM-Keys-Updater-V2`.
4. Dentro do artifact estará `SGM_Keys_Updater_V2_Hekate.zip`, contendo `bootloader/payloads/SGM_Keys_Updater.bin`.
5. Extraia o ZIP na raiz do SD, sem substituir o `hekate` nem o Lockpick original. Inicie Hekate → Payloads → SGM_Keys_Updater.bin.

## Funcionamento

- Na inicialização detecta emuMMC configurada e executa extração nela; caso não haja, usa sysNAND. **Se a emuMMC for mais antiga que a sysNAND**, use o menu original do Lockpick para extrair da sysNAND e gerar as chaves mais atuais.
- A extração existente escreve `sd:/switch/prod.keys`. Somente depois que essa gravação tem sucesso, a alteração prepara `sd:/switch/tinfoil/keys.txt`.
- A exportação valida presença do rótulo `master_key_`, escreve arquivo temporário e verifica tamanho antes de substituir.
- Se já existir `keys.txt`, mantém uma cópia `sd:/switch/tinfoil/keys.sgm.bak`, atualizada em cada execução. Em caso de falha durante a substituição, tenta restaurá-la.
- Mantém o menu original do Lockpick ao finalizar para permitir seleção manual de sysNAND e emuNAND.
- Não comunica chaves pela rede; não inclui chaves na distribuição.

## Testes recomendados

- Backup completo da pasta `sd:/switch/` e, principalmente, de `prod.keys`, `tinfoil/keys.txt`, `tinfoil/keys.sgm.bak`.
- **Primeiro V1:** Hekate → payload → conferir mensagem `SGM: Tinfoil keys.txt updated!` → fechar → abrir Tinfoil → testar arquivo próprio de controle.
- **Depois V2 e OLED**, um console por vez. Exigir que o payload termine sem erro e que `keys.txt` seja maior que 128 bytes. Nunca compartilhe os arquivos de chaves.
- Se aparecer erro de falta de chaves, verificar se a NAND escolhida contém o firmware mais recente. Não altere sigpatches/Atmosphère por este procedimento.
- Se o binário ultrapassar o limite de 128 KiB estabelecido na build, não o injete; o workflow cancela a publicação.

## Compilação local alternativa (Linux/devkitARM)

```sh
git clone --branch 2.0.1 --depth 1 https://github.com/THZoria/Lockpick_RCMaster.git upstream
python3 apply_sgm.py upstream
make -C upstream -j2
# Saída da compilação: upstream/output/Lockpick_RCM.bin
```

## Limitações honestas

Esta entrega contém **a implementação-fonte e a receita automatizada para gerar o payload**, não o `.bin` pronto. O ambiente de execução não disponibilizou devkitARM, Docker nem acesso direto ao arquivo-fonte completo para compilação local. A compilação em GitHub Actions e o funcionamento em V1, V2 e OLED ainda precisam ser confirmados. Não distribua em massa antes de concluir os testes.


## Publicação no repositório criado

1. Extraia o ZIP do projeto em uma pasta do Windows.
2. Com Git para Windows instalado, abra PowerShell nessa pasta.
3. Execute `powershell -ExecutionPolicy Bypass -File .\Publicar_no_GitHub.ps1`.
4. O script cria um clone do repositório, copia os arquivos, faz um commit e envia à `main`; a autenticação é tratada pelo próprio Git, sem senhas no script.
5. Confira o resultado em https://github.com/SGMSteeL1/sgm-keys-updater/actions

Importante: nunca adicione `prod.keys`, `keys.txt` nem qualquer chave real ao Git.
