import pandas as pd
import streamlit as st

from utils.backup import (
    LAST_CLOUD_ERROR_FILE,
    backup_info,
    cloud_is_configured,
    create_backup,
    latest_backup,
    list_backups,
    list_cloud_backups,
    upload_backup_to_drive,
)


def render_backup(conn):
    st.subheader("🛡️ Backup do Sistema")
    st.caption("Backups locais do banco de dados. Eles protegem seus dados antes de qualquer alteração grande.")

    backups = list_backups()
    ultimo = latest_backup()
    cloud_ready = cloud_is_configured()

    c1, c2, c3 = st.columns(3)
    c1.metric("Backups salvos", len(backups))
    c2.metric("Último backup", ultimo.name if ultimo else "Nenhum")
    c3.metric("Google Drive", "Conectado" if cloud_ready else "Não configurado")

    if LAST_CLOUD_ERROR_FILE.exists():
        st.warning(f"Último envio automático para o Drive falhou: {LAST_CLOUD_ERROR_FILE.read_text()}")

    st.divider()

    if st.button("Gerar backup agora", width="stretch"):
        try:
            backup_path = create_backup(prefix="manual")
            if cloud_ready:
                upload_backup_to_drive(backup_path)
            st.success(f"✅ Backup criado: {backup_path.name}")
            if cloud_ready:
                st.success("✅ Backup enviado para o Google Drive.")
            st.rerun()
        except Exception as error:
            st.error(f"Erro ao criar backup: {error}")

    if ultimo and st.button("Enviar último backup para o Google Drive", width="stretch"):
        try:
            upload_backup_to_drive(ultimo)
            st.success("✅ Backup enviado para o Google Drive.")
        except Exception as error:
            st.error(f"Erro ao enviar para o Google Drive: {error}")

    st.divider()
    st.subheader("📦 Backups disponíveis")

    backups = list_backups()

    if not backups:
        st.info("Nenhum backup encontrado ainda.")
        return

    rows = [backup_info(path) for path in backups]
    tabela = pd.DataFrame(rows)
    tabela["tamanho_mb"] = tabela["tamanho_mb"].map(lambda value: f"{value:.2f} MB")
    tabela["criado_em"] = tabela["criado_em"].dt.strftime("%d/%m/%Y %H:%M:%S")
    tabela = tabela.rename(columns={
        "arquivo": "Arquivo",
        "tamanho_mb": "Tamanho",
        "criado_em": "Criado em",
    })

    st.dataframe(
        tabela[["Arquivo", "Tamanho", "Criado em"]],
        width="stretch",
        hide_index=True,
    )

    selected_name = st.selectbox("Selecionar backup para baixar", [path.name for path in backups])
    selected_path = next(path for path in backups if path.name == selected_name)

    with selected_path.open("rb") as file:
        st.download_button(
            "Baixar backup selecionado",
            data=file.read(),
            file_name=selected_path.name,
            mime="application/octet-stream",
            width="stretch",
        )

    st.divider()
    st.subheader("☁️ Backups no Google Drive")

    if not cloud_ready:
        st.warning("Google Drive ainda não está configurado neste computador.")
        return

    cloud_backups = list_cloud_backups()

    if not cloud_backups:
        st.info("Nenhum backup encontrado na pasta do Google Drive.")
        return

    cloud_df = pd.DataFrame(cloud_backups)
    cloud_df["tamanho"] = cloud_df["tamanho"].map(lambda value: f"{value / 1024:.1f} KB")
    cloud_df = cloud_df.rename(columns={
        "arquivo": "Arquivo",
        "tamanho": "Tamanho",
    })
    st.dataframe(cloud_df[["Arquivo", "Tamanho"]], width="stretch", hide_index=True)
