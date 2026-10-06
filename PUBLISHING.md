# Publicar no catálogo de Extensões do IngeTrazo

> **Status: PREPARADO, AINDA NÃO PUBLICADO.**
> Nada foi enviado para nenhum repositório. Este guia só descreve os passos;
> execute-os quando você autorizar (e depois de testar o plugin).
>
> **v1.0.1** é a release que responde à revisão do pull request
> <https://github.com/ingelibre/ingetrazo-extensions/pull/41> — o `Ctrl+Z`
> corrigido para Escala, Rotação, Alinhamento e Espelho com remoção.

Este documento descreve como publicar esta extensão (**IGZ Modify 3D**) no
catálogo <https://github.com/ingelibre/ingetrazo-extensions> (mostrado em
<https://ingetrazo.com/extensiones>).

---

## O que já está pronto

| Item | Onde | Observação |
|---|---|---|
| Código limpo | `igz_tb_modify3d.py` | Artefato `[cite: 1]` removido (linha do `raise`); cabeçalho com **Version: 1.0.1**. |
| Ponto de entrada robusto | `__init__.py` | Carrega `igz_tb_modify3d.py` por caminho de arquivo e expõe `setup(app)` — funciona se o IngeTrazo importar o pacote ou o arquivo. |
| Empacotador | `packaging/build_extension.ps1` (Windows) e `packaging/build_extension.py` (multi-plataforma) | Gera um `.zip` determinístico com **uma** pasta de topo `igz_modify3d/`. |
| Artefato | `dist/igz_modify3d.zip` | Já construído (v1.0.1). **sha256** = `7ae197f031c258e61db197dcdf2d83f74a52f597509e8e679614d6d432e6adf1`. |
| Ficha do catálogo | `ingetrazo-extensions-submission/extensions/igz_modify3d.toml` | Copiar para `extensions/igz_modify3d.toml` no repositório do catálogo. |
| Captura de tela | `ingetrazo-extensions-submission/screenshots/igz_modify3d.png` | Copiar para `screenshots/igz_modify3d.png` (imagem atual de `screenshots/igz-modify-3d.png`). |

O `.zip` contém exatamente uma pasta de topo:

```
igz_modify3d/
├── __init__.py            # setup(app)
├── igz_tb_modify3d.py     # carregador/barra
├── modify3d/
│   ├── igz_mirror3d.py
│   ├── igz_scale3d.py
│   ├── igz_rotate3d.py
│   ├── igz_align3d.py
│   ├── igz_array3d.py
│   ├── igz_polararray3d.py
│   ├── igz_xform_command.py
│   └── icons/*.svg
├── LICENSE
└── README.md
```

O catálogo instala **um arquivo por extensão**: um `.py`, ou um `.zip` com
**uma** pasta contendo um `__init__.py` (ver `TEMPLATE.toml`). Por isso esta
extensão, que é um pacote (barra + subpasta `modify3d/` + ícones), usa `.zip`.

---

## Correção da v1.0.1 (revisão do pull request #41)

A revisão em <https://github.com/ingelibre/ingetrazo-extensions/pull/41> mostrou
que o **Ctrl+Z** não desfazia quatro das seis ferramentas: **Escala**, **Rotação**
e **Alinhamento** alteravam os grupos *no lugar*, e o **Espelho** com "apagar
originais" removia grupos — e o `SnapshotImport` do hospedeiro só sabe reverter
*adições*. Sintoma reportado: depois do *undo*, os objetos continuavam escalados,
rotacionados ou movidos, e no Espelho os originais não voltavam.

Corrigido em **v1.0.1** com `modify3d/igz_xform_command.py`:

- `XformGroupsCommand` guarda, por grupo, o `xform` / `mesh` / `axes` originais
  (e o índice no `scene.groups` quando o grupo é removido) e restaura tudo em
  `undo()`;
- o Espelho com remoção compõe `SnapshotImport` (cópias) + `XformGroupsCommand`
  (`remove_after=True`) através de um `CompositeCommand`.

Matriz e Matriz Polar já eram desfazíveis (apenas adicionam grupos) e não mudaram.

Para responder ao PR, depois de reconstruir o `.zip` e publicar a tag `v1.0.1`:

```powershell
git add -A
git commit -m "fix: undo/redo for Scale, Rotate, Align and Mirror-with-delete (v1.0.1)"
git push origin main
git tag v1.0.1
git push origin v1.0.1
```

Em seguida, no PR do catálogo, atualize `extensions/igz_modify3d.toml`
(`version`, `download` → `v1.0.1` e o novo `sha256`) e comente que a falha de
*undo* foi corrigida.

---

## Passos para publicar (quando autorizar)

1. **Teste o plugin** no IngeTrazo (você pediu para só publicar depois disso).
2. **Confirme as alterações locais e faça o commit.**
   ```powershell
   git add -A
   git commit -m "chore: package for the IngeTrazo extension catalog (v1.0.1)"
   ```
   (Revise `git status`: `screenshots/`, `packaging/` e
   `ingetrazo-extensions-submission/` ainda não estão rastreados.)

3. **(Opcional) Reconstrua o artefato** — só se você mudou o código:
   ```powershell
   powershell -ExecutionPolicy Bypass -File packaging\build_extension.ps1
   ```
   Anote o `sha256` impresso e atualize-o em
   `ingetrazo-extensions-submission/extensions/igz_modify3d.toml`.

4. **Envie o código e crie a tag `v1.0.1`.**
   ```powershell
   git push origin main
   git tag v1.0.1
   git push origin v1.0.1
   ```

5. **Crie a Release `v1.0.1`** em
   <https://github.com/em-rezende/Ingetrazo-igz-modify-3d/releases/new> e
   **anexe `dist/igz_modify3d.zip` como asset** (nome exatamente
   `igz_modify3d.zip`). O `download` da ficha aponta para
   `.../releases/download/v1.0.1/igz_modify3d.zip`.

6. **Abra o pull request no repositório do catálogo.** O fork
   `em-rezende/ingetrazo-extensions` **já existe** (foi usado no igz_toolbars),
   então basta uma branch nova — pelo navegador:
   - *Add file ▸ Create new file* → `extensions/igz_modify3d.toml`, cole o
     conteúdo de
     `ingetrazo-extensions-submission/extensions/igz_modify3d.toml`.
   - *Add file ▸ Upload files* → envie
     `ingetrazo-extensions-submission/screenshots/igz_modify3d.png` como
     `screenshots/igz_modify3d.png`.
   - **Propose changes ▸ Create pull request**.

7. **Responda o checklist** do template do PR:
   - [x] Um arquivo `extensions/igz_modify3d.toml`, copiado de `TEMPLATE.toml`.
   - [x] `download` aponta para uma **tag** (`v1.0.1`), não para uma branch.
   - [x] Testado com a versão do IngeTrazo em `ingetrazo` (**0.5.7**).
   - [x] A licença em `license` é a do código (GPL-3.0-or-later).
   - [x] `reviewed.toml` **não** foi tocado (só mantenedores).
   - Descreva no PR: usa PySide6/Qt; **não** acessa a rede, **não** executa
     programas externos e **não** apaga arquivos.

Um robô revisa a ficha e um mantenedor aprova. A extensão aparece como
**«Comunidade»** até um mantenedor ler o arquivo (aí vira **«Revisada»**).

---

## Detalhes que você pode querer ajustar

- **Versão** (`version = "1.0.1"` e o cabeçalho `# Version: 1.0.1`): ajuste se
  preferir começar por outra.
- **Versão do IngeTrazo** (`ingetrazo = "0.5.7"`): use a versão com que testou.
- **Tags** (`tags = ["productivity", "architecture"]`): válidas são
  `architecture, bim, structures, terrain, drawing, analysis, import-export,
  rendering, fabrication, productivity, education, other`.
- **Captura de tela**: `screenshots/igz-modify-3d.png` mostra a barra e uma
  prévia ao vivo. A sugestão do catálogo é ~1200×750 e o limite é 600 KB; troque
  se quiser.

---

# Publishing to the IngeTrazo extension catalog (EN)

> **Status: PREPARED, NOT YET PUBLISHED.** Nothing has been pushed anywhere.

Everything needed is in place (clean code, a deterministic `.zip` builder, the
entry file and a screenshot). Once you authorise it:

1. Test the plugin in IngeTrazo.
2. Commit locally (`git add -A; git commit -m "chore: package ..."`).
3. (Only if the code changed) rebuild with `packaging\build_extension.ps1`
   and copy the printed `sha256` into the entry.
4. `git push origin main`, then `git tag v1.0.1` and `git push origin v1.0.1`.
5. Create the **v1.0.1** GitHub Release and attach `dist/igz_modify3d.zip` as
   an asset named exactly `igz_modify3d.zip`.
6. In <https://github.com/ingelibre/ingetrazo-extensions>, copy
   `ingetrazo-extensions-submission/extensions/igz_modify3d.toml` to
   `extensions/igz_modify3d.toml` and
   `ingetrazo-extensions-submission/screenshots/igz_modify3d.png` to
   `screenshots/igz_modify3d.png`, then **Create pull request**.
7. Fill in the PR template checklist (no network, no external programs, no
   file deletion).

The **sha256** in the entry
(`7ae197f031c258e61db197dcdf2d83f74a52f597509e8e679614d6d432e6adf1`) is the
fingerprint of `dist/igz_modify3d.zip` as built by the script. It **must**
match the uploaded asset; if you rebuild, update the value.
