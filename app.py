import streamlit as st
import pandas as pd
import os
import json

# Import local modules
import data_manager
from rules_engine import RulesEngine

# Try to import plotly, fallback to streamlit native charts if not available
try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# Set page config
st.set_page_config(
    page_title="SSD - Sistema de Recomendação Up-sell (Grupo 6)",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Design
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
}

/* Custom cards for recommendations */
.rec-card {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(168, 85, 247, 0.05) 100%);
    border: 1px solid rgba(99, 102, 241, 0.15);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 15px;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.rec-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(99, 102, 241, 0.1);
}

.badge-discount {
    background-color: #ef4444;
    color: white;
    padding: 3px 8px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    display: inline-block;
    margin-bottom: 8px;
}

.price-old {
    text-decoration: line-through;
    color: #9ca3af;
    font-size: 0.9rem;
    margin-right: 8px;
}

.price-new {
    color: #10b981;
    font-size: 1.3rem;
    font-weight: 700;
}

.reasoning-box {
    background-color: rgba(59, 130, 246, 0.06);
    border-left: 4px solid #3b82f6;
    padding: 10px 15px;
    border-radius: 0 8px 8px 0;
    margin-top: 10px;
    font-size: 0.9rem;
}

.simon-header {
    background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%);
    color: white;
    padding: 15px 25px;
    border-radius: 12px;
    margin-bottom: 25px;
}
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "cart" not in st.session_state:
    st.session_state.cart = {}  # prod_id -> quantity
if "client_type" not in st.session_state:
    st.session_state.client_type = "Qualquer"
if "conversions" not in st.session_state:
    st.session_state.conversions = []  # List of dicts representing completed checkouts
if "last_recommendations" not in st.session_state:
    st.session_state.last_recommendations = []

# Instantiate Rules Engine
engine = RulesEngine()

# Helpers
def reset_to_defaults():
    # Initial catalog
    default_catalog = [
        {"id": "cam_01", "name": "Câmara DSLR Profissional", "category": "Câmaras", "price": 850.00, "margin": 0.25},
        {"id": "cam_02", "name": "Câmara de Ação 4K", "category": "Câmaras", "price": 299.00, "margin": 0.30},
        {"id": "acc_01", "name": "Tripé de Alumínio Estável", "category": "Acessórios", "price": 49.99, "margin": 0.50},
        {"id": "acc_02", "name": "Cartão de Memória SD 128GB (Ultra)", "category": "Acessórios", "price": 24.99, "margin": 0.60},
        {"id": "acc_03", "name": "Bateria Recarregável Extra", "category": "Acessórios", "price": 39.99, "margin": 0.45},
        {"id": "lap_01", "name": "Portátil Gaming 16\"", "category": "Portáteis", "price": 1250.00, "margin": 0.15},
        {"id": "lap_02", "name": "Portátil Ultrabook Trabalho", "category": "Portáteis", "price": 899.00, "margin": 0.18},
        {"id": "lap_acc_01", "name": "Rato Sem Fios Ergonómico", "category": "Acessórios Portáteis", "price": 29.99, "margin": 0.55},
        {"id": "lap_acc_02", "name": "Mochila Impermeável para Portátil", "category": "Acessórios Portáteis", "price": 45.00, "margin": 0.50},
        {"id": "srv_01", "name": "Extensão de Garantia (+3 anos)", "category": "Serviços", "price": 79.99, "margin": 0.85},
        {"id": "srv_02", "name": "Seguro Contra Roubo e Danos (Anual)", "category": "Serviços", "price": 119.99, "margin": 0.80},
        {"id": "phn_01", "name": "Smartphone Flagship 5G", "category": "Telemóveis", "price": 999.00, "margin": 0.20},
        {"id": "phn_acc_01", "name": "Capa Protetora de Silicone", "category": "Acessórios Telemóveis", "price": 19.99, "margin": 0.70},
        {"id": "phn_acc_02", "name": "Carregador Rápido 45W", "category": "Acessórios Telemóveis", "price": 29.99, "margin": 0.60}
    ]
    # Initial rules
    default_rules = [
        {
            "id": "rule_01",
            "name": "Up-sell Câmara -> Cartão SD",
            "conditions": {"has_product_in_cart": [], "has_category_in_cart": ["Câmaras"], "min_cart_total": 0.0, "client_type": "Qualquer"},
            "actions": {"recommend_product_id": "acc_02", "discount_percent": 10.0, "priority_score": 10},
            "explanation": "Como adicionou uma câmara ao carrinho, sugerimos o Cartão de Memória SD 128GB (Ultra) para poder começar a fotografar de imediato!",
            "active": True
        },
        {
            "id": "rule_02",
            "name": "Up-sell Câmara Alta Gama -> Tripé",
            "conditions": {"has_product_in_cart": ["cam_01"], "has_category_in_cart": [], "min_cart_total": 500.0, "client_type": "Qualquer"},
            "actions": {"recommend_product_id": "acc_01", "discount_percent": 15.0, "priority_score": 15},
            "explanation": "Para câmaras de qualidade profissional, sugerimos o Tripé de Alumínio Estável para fotos e vídeos com máxima estabilidade.",
            "active": True
        },
        {
            "id": "rule_03",
            "name": "Mochila para Portátil",
            "conditions": {"has_product_in_cart": [], "has_category_in_cart": ["Portáteis"], "min_cart_total": 0.0, "client_type": "Qualquer"},
            "actions": {"recommend_product_id": "lap_acc_02", "discount_percent": 5.0, "priority_score": 8},
            "explanation": "Proteja o seu novo portátil contra quedas e chuva com a Mochila Impermeável para Portátil.",
            "active": True
        },
        {
            "id": "rule_04",
            "name": "Oferta Especial VIP Portátil -> Rato",
            "conditions": {"has_product_in_cart": [], "has_category_in_cart": ["Portáteis"], "min_cart_total": 0.0, "client_type": "VIP"},
            "actions": {"recommend_product_id": "lap_acc_01", "discount_percent": 20.0, "priority_score": 12},
            "explanation": "Como cliente VIP, oferecemos-lhe 20% de desconto no Rato Sem Fios Ergonómico para completar a sua estação de trabalho.",
            "active": True
        },
        {
            "id": "rule_05",
            "name": "Seguro de Proteção de Valor Elevado",
            "conditions": {"has_product_in_cart": [], "has_category_in_cart": [], "min_cart_total": 300.0, "client_type": "Qualquer"},
            "actions": {"recommend_product_id": "srv_02", "discount_percent": 10.0, "priority_score": 5},
            "explanation": "Para carrinhos de compras de valor superior a 300€, recomendamos a subscrição do Seguro Contra Roubo e Danos.",
            "active": True
        },
        {
            "id": "rule_06",
            "name": "Acessórios de Telemóvel -> Capa",
            "conditions": {"has_product_in_cart": [], "has_category_in_cart": ["Telemóveis"], "min_cart_total": 0.0, "client_type": "Qualquer"},
            "actions": {"recommend_product_id": "phn_acc_01", "discount_percent": 10.0, "priority_score": 9},
            "explanation": "Proteja o seu smartphone contra riscos e quedas com a Capa Protetora de Silicone.",
            "active": True
        }
    ]
    data_manager.save_catalog(default_catalog)
    data_manager.save_rules(default_rules)
    engine.refresh_rules()
    st.session_state.cart = {}
    st.session_state.conversions = []

# Sidebar Navigation and Configuration
with st.sidebar:
    st.image("https://img.icons8.com/color/96/shopping-bags.png", width=80)
    st.title("SSD Up-sell Manager")
    st.markdown("### **Grupo 6 - Mestrado**")
    st.markdown("Protótipo de Sistema de Suporte à Decisão baseado no Processo de Tomada de Decisão de **Herbert Simon**.")
    
    st.markdown("---")
    st.markdown("### **Configuração do Cliente**")
    st.session_state.client_type = st.selectbox(
        "Tipo de Cliente (Contexto)",
        ["Qualquer", "Novo", "Recorrente", "VIP"],
        index=0,
        help="Simula o perfil do utilizador atual no checkout para ativação de regras específicas (ex: Regras VIP)."
    )
    
    st.markdown("---")
    st.markdown("### **Manutenção do Sistema**")
    if st.button("Restaurar Configuração Padrão", use_container_width=True, type="secondary"):
        reset_to_defaults()
        st.success("Dados restaurados com sucesso!")
        st.rerun()

# Title banner
st.title("🛒 Sistema de Recomendação de Produtos (Up-sell)")
st.markdown("Este SSD decide automaticamente que produtos complementares sugerir ao utilizador no checkout para otimizar vendas e margens.")

# Tabs matching Simon's phases
tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 1. Fase de Intelligence (Dados)", 
    "📐 2. Fase de Design (Regras)", 
    "⚡ 3. Fase de Choice (Inferência)", 
    "💻 4. Fase de Implementation (Simulador)"
])

# ==========================================
# 1. FASE DE INTELLIGENCE (DADOS)
# ==========================================
with tab1:
    st.markdown('<div class="simon-header"><h3>Fase de Intelligence: Identificação e Exploração de Dados</h3>'
                '<p>Nesta fase são mapeados os dados sobre o catálogo de produtos e margens de lucro, servindo como a base de conhecimento do SSD.</p></div>', unsafe_allow_html=True)
    
    # Load data
    catalog = data_manager.load_catalog()
    df_catalog = pd.DataFrame(catalog)
    
    # Stats overview
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total de Produtos", len(df_catalog))
    with c2:
        st.metric("Categorias Únicas", len(df_catalog["category"].unique()))
    with c3:
        st.metric("Preço Médio", f"{df_catalog['price'].mean():.2f} €")
    with c4:
        st.metric("Margem Média", f"{df_catalog['margin'].mean()*100:.1f} %")
        
    st.markdown("---")
    
    # Visual catalog exploration
    col_left, col_right = st.columns([3, 2])
    with col_left:
        st.subheader("Catálogo de Produtos")
        st.dataframe(
            df_catalog.rename(columns={
                "id": "ID",
                "name": "Nome do Produto",
                "category": "Categoria",
                "price": "Preço (€)",
                "margin": "Margem de Lucro"
            }),
            use_container_width=True,
            hide_index=True
        )
        
    with col_right:
        st.subheader("Análise de Margem por Categoria")
        if not df_catalog.empty:
            df_cat_margin = df_catalog.groupby("category")[["price", "margin"]].mean().reset_index()
            df_cat_margin["margin_pct"] = df_cat_margin["margin"] * 100
            
            if HAS_PLOTLY:
                fig = px.bar(
                    df_cat_margin, 
                    x="category", 
                    y="margin_pct", 
                    labels={"category": "Categoria", "margin_pct": "Margem Média (%)"},
                    color="category",
                    text_auto=".1f"
                )
                fig.update_layout(showlegend=False, height=300, margin=dict(l=20, r=20, t=10, b=20))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.bar_chart(df_cat_margin.set_index("category")["margin_pct"])
        else:
            st.info("Catálogo vazio.")
            
    st.markdown("---")
    st.subheader("➕ Adicionar Novo Produto ao Catálogo")
    with st.form("new_product_form", clear_on_submit=True):
        f_id = st.text_input("ID do Produto (ex: acc_04)")
        f_name = st.text_input("Nome do Produto")
        f_category = st.selectbox("Categoria", ["Câmaras", "Acessórios", "Portáteis", "Acessórios Portáteis", "Telemóveis", "Acessórios Telemóveis", "Serviços"])
        f_price = st.number_input("Preço (€)", min_value=0.01, step=0.01, value=10.00)
        f_margin = st.slider("Margem de Lucro", min_value=0.01, max_value=0.95, value=0.30, step=0.01)
        
        submitted = st.form_submit_button("Inserir Produto no Catálogo")
        if submitted:
            if not f_id or not f_name:
                st.error("Por favor, preencha o ID e o Nome do produto.")
            elif any(p["id"] == f_id for p in catalog):
                st.error(f"Já existe um produto com o ID '{f_id}'.")
            else:
                new_prod = {
                    "id": f_id,
                    "name": f_name,
                    "category": f_category,
                    "price": f_price,
                    "margin": f_margin
                }
                catalog.append(new_prod)
                data_manager.save_catalog(catalog)
                st.success(f"Produto '{f_name}' adicionado com sucesso!")
                st.rerun()

    with tab2:
        st.markdown('<div class="simon-header"><h3>Fase de Design: Modelação de Regras e Critérios</h3>'
                    '<p>Nesta fase são modeladas as regras de negócio em formato de Tabelas de Decisão. Cada regra especifica condições e a recomendação resultante.</p></div>', unsafe_allow_html=True)
        
        st.success("🟢 **Ligação à Cloud Ativa:** O motor de decisão está integrado em tempo real com o DecisionRules.io!")
        
        # Showcase the architecture
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.subheader("🔧 Configurações da API Cloud")
            st.markdown("""
            O sistema externalizou as regras locais para uma plataforma **BRMS (Business Rules Management System)**.
            - **Provedor:** [DecisionRules.io](https://www.decisionrules.io)
            - **ID da Regra (Rule ID):** `687f7caf-1ba8-6060-9ce5-1cad6e86dd2d`
            - **Versão:** `v1` (Versão de Produção)
            - **Estado do Endpoint:** `Ativo & Pronto`
            - **Autenticação:** `Bearer Token` (Solver API Key)
            """)
            
            # Link to console
            st.link_button("Abrir Consola DecisionRules.io", "https://app.decisionrules.io", type="primary", use_container_width=True)
            
        with col_info2:
            st.subheader("💡 Vantagens desta Arquitetura")
            st.markdown("""
            * **Desacoplamento:** A lógica de Up-sell foi retirada do código Python, facilitando a manutenção e alteração de regras sem reiniciar a aplicação.
            * **Modelação Visual:** As regras são desenhadas de forma intuitiva como tabelas de decisão visuais no portal.
            * **Independência de Negócio:** Gestores de marketing podem adicionar novas campanhas e alterar descontos instantaneamente sem precisar de programadores.
            * **Versionamento:** Suporte nativo para gerir versões de regras (ex: criar rascunhos e publicar apenas quando testadas).
            """)
            
        st.markdown("---")
        st.subheader("📊 Modelação da Tabela de Decisão")
        st.markdown("""
        As regras foram desenhadas no DecisionRules com o seguinte mapeamento de variáveis:
        
        * **Entradas (Inputs):**
          - `client_type` (Perfil de Cliente: Novo, Recorrente, VIP)
          - `min_cart_total` (Subtotal mínimo no checkout)
          - `has_product_in_cart` (Verificação se um produto específico está no carrinho)
          - `has_category_in_cart` (Verificação se uma categoria de produto está no carrinho)
        
        * **Saídas (Outputs):**
          - `recommend_product_id` (Produto a ser sugerido)
          - `discount_percent` (Desconto comercial a aplicar)
          - `priority_score` (Critério de desempate)
          - `explanation` (Mensagem explicativa para a Decision Support Facility)
        """)
        
        st.info("ℹ️ **Nota de Modelação:** Todas as regras (como a de Up-sell de Câmaras para Cartões SD, Mochilas para Portáteis ou Desconto VIP) estão registadas na plataforma Cloud e são chamadas em tempo real durante a simulação da compra.")

# ==========================================
# 3. FASE DE CHOICE (INFERÊNCIA)
# ==========================================
with tab3:
                st.success("Regra inserida com sucesso!")
                st.rerun()

# ==========================================
# 3. FASE DE CHOICE (INFERÊNCIA)
# ==========================================
with tab3:
    st.markdown('<div class="simon-header"><h3>Fase de Choice: Critérios de Inferência e Escolha</h3>'
                '<p>Nesta fase é simulada a decisão do motor de regras. Definem-se as estratégias de ordenação das recomendações e resolução de conflitos.</p></div>', unsafe_allow_html=True)
    
    st.subheader("Como Funciona a Escolha no Nosso SSD")
    st.markdown("""
    O motor de inferência segue os seguintes passos lógicos para decidir o que apresentar ao cliente:
    1. **Filtro de Atividade**: Apenas regras com `active = True` são consideradas.
    2. **Filtro de Contexto/Carrinho**: As condições da regra (produtos, categorias, total do carrinho, perfil de cliente) têm de ser satisfeitas.
    3. **Filtro de Evitação de Duplicados**: Não sugerimos um produto que o utilizador **já tem** no carrinho.
    4. **Resolução de Conflitos (Ranking)**: Se várias regras gerarem recomendações para o mesmo produto, ou se quisermos limitar o número de sugestões visíveis, ordenamos com base nos seguintes critérios prioritários:
        *   **1º Score de Prioridade** (Definido pelo gestor)
        *   **2º Desconto Oferecido** (%)
        *   **3º Margem de Lucro** do produto (Proteção do negócio)
    """)
    
    st.markdown("---")
    st.subheader("🔍 Consola de Depuração do Motor de Escolha")
    st.markdown("Escolha um cenário de teste abaixo para simular instantaneamente a inferência e ver o processo de decisão:")
    
    # Sample carts to test
    preset_cart = st.selectbox(
        "Selecionar Carrinho de Teste",
        [
            "Carrinho Vazio",
            "Câmara DSLR Profissional (cam_01)",
            "Portátil Gaming (lap_01) + Cliente VIP",
            "Carrinho de Alto Valor (Sem Câmaras)",
            "Smartphone 5G (phn_01)"
        ]
    )
    
    # Build simulated items for evaluation
    sim_items = []
    sim_client = st.session_state.client_type
    
    if preset_cart == "Câmara DSLR Profissional (cam_01)":
        sim_items = [{"product_id": "cam_01", "name": "Câmara DSLR Profissional", "category": "Câmaras", "price": 850.00, "quantity": 1}]
    elif preset_cart == "Portátil Gaming (lap_01) + Cliente VIP":
        sim_items = [{"product_id": "lap_01", "name": "Portátil Gaming 16\"", "category": "Portáteis", "price": 1250.00, "quantity": 1}]
        sim_client = "VIP"
    elif preset_cart == "Carrinho de Alto Valor (Sem Câmaras)":
        sim_items = [
            {"product_id": "lap_02", "name": "Portátil Ultrabook Trabalho", "category": "Portáteis", "price": 899.00, "quantity": 1},
            {"product_id": "phn_01", "name": "Smartphone Flagship 5G", "category": "Telemóveis", "price": 999.00, "quantity": 1}
        ]
    elif preset_cart == "Smartphone 5G (phn_01)":
        sim_items = [{"product_id": "phn_01", "name": "Smartphone Flagship 5G", "category": "Telemóveis", "price": 999.00, "quantity": 1}]
        
    st.write(f"**Dados de Entrada de Teste:**")
    st.write(f"- Perfil: `{sim_client}`")
    st.write(f"- Itens do Carrinho:")
    if sim_items:
        st.json(sim_items)
    else:
        st.write("*Carrinho Vazio*")
        
    # Evaluate
    engine.refresh_rules()
    recs = engine.evaluate(sim_items, sim_client)
    
    st.markdown("#### **Resultado da Inferência (Recomendações Ordenadas):**")
    if recs:
        st.success(f"O motor de inferência identificou {len(recs)} recomendação(ões) válida(s).")
        
        # Display decision ranking table
        df_recs = pd.DataFrame(recs)
        st.dataframe(
            df_recs[[
                "priority_score", "product_name", "discount_percent", "original_price", 
                "discounted_price", "margin", "rule_name", "explanation"
            ]].rename(columns={
                "priority_score": "Score (Prioridade)",
                "product_name": "Recomendação",
                "discount_percent": "Desconto (%)",
                "original_price": "Preço Base (€)",
                "discounted_price": "Preço Final (€)",
                "margin": "Margem Comercial",
                "rule_name": "Regra Ativada",
                "explanation": "Explicação / Justificação"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("Nenhuma recomendação ativada para as condições dadas (ou todos os produtos sugeridos já se encontram no carrinho).")

# ==========================================
# 4. FASE DE IMPLEMENTATION (SIMULADOR)
# ==========================================
with tab4:
    st.markdown('<div class="simon-header"><h3>Fase de Implementation: Interface e Métricas de Impacto</h3>'
                '<p>Simulação real do checkout. O cliente navega pela loja, e as recomendações aparecem em tempo real. Avaliam-se as taxas de aceitação.</p></div>', unsafe_allow_html=True)
    
    # Store simulated stats
    col_store, col_cart = st.columns([5, 3])
    
    with col_store:
        st.subheader("🛒 Catálogo de Vendas (Simulador de Loja)")
        st.markdown("Adicione produtos ao seu carrinho:")
        
        # Display items in responsive columns
        cat_items = data_manager.load_catalog()
        
        # Group products by category
        grouped_items = {}
        for item in cat_items:
            grouped_items.setdefault(item["category"], []).append(item)
            
        for cat_name, items in grouped_items.items():
            st.markdown(f"##### **{cat_name}**")
            cols = st.columns(3)
            for idx, item in enumerate(items):
                col_target = cols[idx % 3]
                with col_target:
                    with st.container(border=True):
                        st.markdown(f"**{item['name']}**")
                        st.markdown(f"**{item['price']:.2f} €**")
                        
                        # Add button
                        btn_key = f"add_{item['id']}"
                        if st.button("Adicionar", key=btn_key, use_container_width=True):
                            st.session_state.cart[item['id']] = st.session_state.cart.get(item['id'], 0) + 1
                            st.rerun()
                            
    with col_cart:
        st.subheader("🛍️ O Seu Carrinho")
        
        cart_items_list = []
        subtotal = 0.0
        
        if st.session_state.cart:
            for pid, qty in list(st.session_state.cart.items()):
                if qty <= 0:
                    continue
                prod = data_manager.get_product_by_id(pid)
                if prod:
                    item_total = prod["price"] * qty
                    subtotal += item_total
                    cart_items_list.append({
                        "product_id": pid,
                        "name": prod["name"],
                        "category": prod["category"],
                        "price": prod["price"],
                        "quantity": qty,
                        "total": item_total
                    })
                    
                    # Row in cart with remove button
                    c_name, c_qty, c_btn = st.columns([4, 2, 2])
                    with c_name:
                        st.write(f"**{prod['name']}**")
                        st.caption(f"{prod['price']:.2f} € cada")
                    with c_qty:
                        st.write(f"Qtd: {qty}")
                    with c_btn:
                        if st.button("Remover", key=f"rem_{pid}"):
                            st.session_state.cart[pid] -= 1
                            if st.session_state.cart[pid] <= 0:
                                del st.session_state.cart[pid]
                            st.rerun()
            st.markdown("---")
            st.markdown(f"#### **Subtotal: {subtotal:.2f} €**")
            
            # Clear cart button
            if st.button("Esvaziar Carrinho", use_container_width=True):
                st.session_state.cart = {}
                st.rerun()
        else:
            st.info("O seu carrinho está vazio. Adicione produtos para ativar o SSD.")
            
    # Evaluation / Recommendations Section
    st.markdown("---")
    st.subheader("🎯 Sugestões Personalizadas para Si (Saída do SSD)")
    
    if cart_items_list:
        engine.refresh_rules()
        recommendations = engine.evaluate(cart_items_list, st.session_state.client_type)
        st.session_state.last_recommendations = recommendations
        
        if recommendations:
            st.success("O nosso sistema detetou oportunidades de Up-sell. Aproveite estas ofertas:")
            
            # Show up to 3 recommendations
            rec_cols = st.columns(min(len(recommendations), 3))
            
            for index, rec in enumerate(recommendations[:3]):
                with rec_cols[index]:
                    # Build beautiful custom card
                    st.markdown(
                        f"""
                        <div class="rec-card">
                            <span class="badge-discount">-{rec['discount_percent']:.0f}% Desconto Especial</span>
                            <h4>{rec['product_name']}</h4>
                            <span class="price-old">{rec['original_price']:.2f} €</span>
                            <span class="price-new">{rec['discounted_price']:.2f} €</span>
                            <div class="reasoning-box">
                                💡 <b>Explicação (SSD):</b><br>
                                <i>{rec['explanation']}</i>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    # Accept button
                    if st.button(f"Aceitar Oferta: {rec['product_name']}", key=f"acc_rec_{rec['product_id']}_{index}", use_container_width=True, type="primary"):
                        # Add recommendation to cart (with the rule discount applied by modifying quantity/price mapping)
                        # To keep it simple, we add it with its standard ID. The discount is handled for the metrics.
                        st.session_state.cart[rec['product_id']] = st.session_state.cart.get(rec['product_id'], 0) + 1
                        
                        # Record successful conversion
                        st.session_state.conversions.append({
                            "type": "up_sell_accepted",
                            "rule_id": rec["rule_id"],
                            "product_id": rec["product_id"],
                            "discount": rec["discount_percent"],
                            "price": rec["discounted_price"],
                            "margin": rec["margin"]
                        })
                        st.toast(f"Adicionou {rec['product_name']} com sucesso!", icon="🎉")
                        st.rerun()
        else:
            st.info("Nenhuma recomendação adicional para o carrinho atual.")
    else:
        st.caption("Adicione produtos ao carrinho para visualizar as recomendações do motor de decisão.")
        
    st.markdown("---")
    st.subheader("📊 Painel de Avaliação de Eficácia do SSD")
    st.markdown("Métricas em tempo real sobre a eficácia do SSD de Up-sell simulado neste painel:")
    
    total_conversions = len(st.session_state.conversions)
    total_revenue = sum(c["price"] for c in st.session_state.conversions if c["type"] == "up_sell_accepted")
    avg_discount = sum(c["discount"] for c in st.session_state.conversions) / total_conversions if total_conversions > 0 else 0
    total_margin = sum(c["price"] * c["margin"] for c in st.session_state.conversions)
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Up-sells Aceites", total_conversions)
    with m2:
        st.metric("Faturação Up-sell", f"{total_revenue:.2f} €")
    with m3:
        st.metric("Desconto Médio Oferecido", f"{avg_discount:.1f} %")
    with m4:
        st.metric("Margem Estimada Recuperada", f"{total_margin:.2f} €")
        
    if total_conversions > 0:
        st.markdown("**Regras mais bem-sucedidas (Regras com Conversões):**")
        df_conv = pd.DataFrame(st.session_state.conversions)
        df_rule_count = df_conv.groupby("rule_id").size().reset_index(name="Conversões")
        st.dataframe(df_rule_count, use_container_width=True, hide_index=True)
