import streamlit as st
import pandas as pd
import io
import re
import zipfile

def process_excel_data(df):
    """
    Processa os dados do Excel conforme as especificações do usuário
    """
    processed_df = df.copy()
    
    processed_df.rename(columns={
        'Pedido': 'PEDIDO',
        'Sku': 'SKU',
        'Ean Produto': 'EAN_PRODUTO',
        'Quantidade': 'QUANT'
    }, inplace=True)

    # 1º NOME DO SAPATO - 10 primeiros caracteres da coluna SKU
    processed_df["NOME_DO_SAPATO"] = processed_df["SKU"].astype(str).str[:10]
    
    # 2º MARCA - primeiro caractere da coluna SKU
    processed_df["MARCA"] = processed_df["SKU"].astype(str).str[0]
    
    # 3º LINHA - 5 primeiros caracteres numéricos da coluna SKU
    def extract_first_5_numeric(sku):
        sku_str = str(sku)
        numeric_chars = re.findall(r"\d", sku_str)
        return "".join(numeric_chars[:5])
    
    processed_df["LINHA"] = processed_df["SKU"].apply(extract_first_5_numeric)
    
    # 4º MODELO - do sétimo ao décimo caractere da coluna SKU
    processed_df["MODELO"] = processed_df["SKU"].astype(str).str[6:10]
    
    # 5º SEQUENCIA - do décimo primeiro ao décimo quarto caractere da coluna SKU
    def extract_sequence(sku):
        sku_str = str(sku)
        if len(sku_str) >= 14:
            return sku_str[10:14]
        else:
            return ""
    
    processed_df["SEQUENCIA"] = processed_df["SKU"].apply(extract_sequence)
    
    # 6º SEQ - último caractere da coluna SKU
    processed_df["SEQ"] = processed_df["SKU"].astype(str).str[-1]
    
    # 7º NUM_DA_ETQ - coluna vazia
    processed_df["NUM_DA_ETQ"] = ""
    
    # 8º VALOR_DO_FILTRO - valor 1 em todas as linhas
    processed_df["VALOR_DO_FILTRO"] = 1
    
    # 9º PREFIXO_DA_EMP - 7 primeiros caracteres da coluna EAN_PRODUTO
    processed_df["PREFIXO_DA_EMP"] = processed_df["EAN_PRODUTO"].astype(str).str[:7]
    
    # 10º ITEM_DE_REF - do oitavo ao décimo segundo caractere + zero na frente
    def extract_item_ref(ean):
        ean_str = str(ean)
        if len(ean_str) >= 12:
            extracted = ean_str[7:12]
            return "0" + extracted
        else:
            return "0"
    
    processed_df["ITEM_DE_REF"] = processed_df["EAN_PRODUTO"].apply(extract_item_ref)
    
    # 11º SERIAL - coluna vazia
    processed_df["SERIAL"] = ""

    # Gerar linhas baseado na coluna QUANT (1 linha por unidade)
    expanded_rows = []
    for index, row in processed_df.iterrows():
        try:
            quant = int(float(str(row["QUANT"]).strip()))
        except (ValueError, TypeError):
            quant = 1
        quant = max(1, quant)
        # Adicionar a linha original
        expanded_rows.append(row.copy())
        # Adicionar (quant - 1) linhas adicionais com os mesmos dados
        for i in range(quant - 1):
            extra_row = row.copy()
            extra_row["NUM_DA_ETQ"] = ""
            extra_row["SERIAL"] = ""
            expanded_rows.append(extra_row)
    
    final_df = pd.DataFrame(expanded_rows)
    
    # Formatar todas as colunas como texto
    for col in final_df.columns:
        final_df[col] = final_df[col].astype(str)

    return final_df

def main():
    st.set_page_config(
        page_title="Processador de Excel - Sapatos",
        page_icon="👟",
        layout="wide"
    )
    
    st.title("👟 Processador de Excel - Dados de Sapatos")
    st.markdown("---")
    
    st.markdown("""
    ### Instruções:
    1. Faça upload do arquivo Excel (.xlsx ou .xlsm)
    2. O sistema processará automaticamente os dados conforme as regras especificadas
    3. Baixe o arquivo processado
    """)
    
    st.markdown("---")
    
    uploaded_file = st.file_uploader(
        "Escolha o arquivo Excel",
        type=["xlsx", "xlsm"],
        help="Selecione um arquivo Excel (.xlsx ou .xlsm)"
    )
    
    if uploaded_file is not None:
        try:
            with st.spinner("Lendo arquivo Excel..."):
                df = pd.read_excel(uploaded_file, engine="openpyxl")
            
            st.success(f"Arquivo carregado com sucesso! {len(df)} linhas encontradas.")
            
            st.subheader("📋 Preview dos Dados Originais")
            st.dataframe(df.head(10), use_container_width=True)
            
            required_columns = ["Sku", "Ean Produto", "Quantidade", "Pedido"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                st.error(f"Colunas obrigatórias não encontradas: {missing_columns}")
                st.info("Colunas disponíveis no arquivo:")
                st.write(list(df.columns))
            else:
                with st.spinner("Processando dados e gerando arquivos por pedido..."):
                    processed_df = process_excel_data(df)
                
                st.success(f"Dados processados com sucesso! {len(processed_df)} linhas geradas.")
                
                st.subheader("✅ Preview dos Dados Processados")
                st.dataframe(processed_df.head(20), use_container_width=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Linhas Originais", len(df))
                with col2:
                    st.metric("Linhas Processadas", len(processed_df))
                with col3:
                    st.metric("Expansão", f"{len(processed_df)/len(df):.1f}x")
                
                st.subheader("💾 Download dos Arquivos Processados por Pedido")
                
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for pedido, group_df in processed_df.groupby('PEDIDO'):
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            group_df.to_excel(writer, index=False, sheet_name=f'Pedido_{pedido}')
                            workbook  = writer.book
                            worksheet = writer.sheets[f'Pedido_{pedido}']
                            text_format = workbook.add_format({'num_format': '@'})
                            for col_num, value in enumerate(group_df.columns.values):
                                worksheet.set_column(col_num, col_num, None, text_format)
                        zipf.writestr(f'Pedido_{pedido}.xlsx', output.getvalue())
                
                zip_buffer.seek(0)
                
                st.download_button(
                    label="📥 Baixar Todos os Arquivos Excel (.zip)",
                    data=zip_buffer.getvalue(),
                    file_name="pedidos_processados.zip",
                    mime="application/zip"
                )
                
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {str(e)}")
            st.info("Verifique se o arquivo está no formato correto e não está corrompido. Certifique-se de que as colunas 'Pedido', 'Sku', 'Ean Produto' e 'Quantidade' existem.")

if __name__ == "__main__":
    main()
