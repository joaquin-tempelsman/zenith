"""
Streamlit Dashboard for Voice-Managed Inventory System.
Provides UI for viewing inventory and running SQL queries.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date
from sqlalchemy.orm import Session
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.config import settings
from src.database.models import SessionLocal, init_db
from src.database import crud


def check_authentication():
    """
    Check if user is authenticated via session state.
    
    Returns:
        True if authenticated, False otherwise
    """
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    return st.session_state.authenticated


def login_page():
    """
    Display login page for dashboard access.
    """
    st.title("🔐 Inventory Dashboard Login")
    
    st.markdown("---")
    
    password = st.text_input("Enter Password", type="password", key="login_password")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        if st.button("🔓 Login", use_container_width=True):
            if password == settings.dashboard_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ Incorrect password. Please try again.")
    
    st.markdown("---")
    st.info("💡 Default password is set in the `.env` file (`DASHBOARD_PASSWORD`)")


def logout():
    """
    Log out the current user.
    """
    st.session_state.authenticated = False
    st.rerun()


def get_db_session() -> Session:
    """
    Get a database session.

    Returns:
        Database session instance
    """
    # Create a new session with autoflush to ensure fresh data
    session = SessionLocal()
    # Expire all objects to force reload from database
    session.expire_all()
    return session


def inventory_tab():
    """
    Display the Inventory tab with all items.
    """
    st.header("📦 Inventory Overview")
    
    # Get database session
    db = get_db_session()
    
    try:
        # Get all items
        items = crud.get_all_items(db)
        
        if not items:
            st.info("📭 No items in inventory yet. Add items via Telegram bot!")
            return
        
        # Convert to dataframe
        items_data = [item.to_dict() for item in items]
        df = pd.DataFrame(items_data)
        
        # Format dates
        if "last_updated" in df.columns:
            df["last_updated"] = pd.to_datetime(df["last_updated"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        
        if "expire_date" in df.columns:
            df["expire_date"] = df["expire_date"].fillna("N/A")
        
        # Display statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Items", len(items))
        
        with col2:
            total_quantity = df["quantity"].sum()
            st.metric("Total Quantity", total_quantity)
        
        with col3:
            categories = df["category"].nunique()
            st.metric("Categories", categories)
        
        with col4:
            low_stock = len(df[df["quantity"] < 5])
            st.metric("Low Stock Items", low_stock, delta_color="inverse")
        
        st.markdown("---")
        
        # Filters
        st.subheader("🔍 Filters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            categories_list = ["All"] + sorted(df["category"].unique().tolist())
            selected_category = st.selectbox("Category", categories_list)
        
        with col2:
            sort_by = st.selectbox(
                "Sort By",
                ["name", "quantity", "category", "last_updated"],
                index=0
            )
        
        # Apply filters
        filtered_df = df.copy()
        if selected_category != "All":
            filtered_df = filtered_df[filtered_df["category"] == selected_category]
        
        # Sort
        filtered_df = filtered_df.sort_values(by=sort_by)
        
        st.markdown("---")
        
        # Display dataframe
        st.subheader("📊 Inventory Data")
        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": "ID",
                "name": st.column_config.TextColumn("Item Name", width="medium"),
                "quantity": st.column_config.NumberColumn("Quantity", format="%d"),
                "category": st.column_config.TextColumn("Category", width="small"),
                "expire_date": st.column_config.TextColumn("Expiration Date", width="small"),
                "last_updated": st.column_config.TextColumn("Last Updated", width="medium"),
            }
        )
        
        # Category breakdown
        st.markdown("---")
        st.subheader("📈 Category Breakdown")
        
        category_summary = df.groupby("category").agg({
            "quantity": "sum",
            "id": "count"
        }).reset_index()
        category_summary.columns = ["Category", "Total Quantity", "Item Count"]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.bar_chart(category_summary.set_index("Category")["Item Count"])
            st.caption("Items per Category")
        
        with col2:
            st.bar_chart(category_summary.set_index("Category")["Total Quantity"])
            st.caption("Total Quantity per Category")
        
        # Low stock warning
        if low_stock > 0:
            st.markdown("---")
            st.warning(f"⚠️ {low_stock} items have low stock (quantity < 5)")
            low_stock_items = df[df["quantity"] < 5][["name", "quantity", "category"]]
            st.dataframe(low_stock_items, hide_index=True, use_container_width=True)
        
        # Expiring soon items
        if "expire_date" in df.columns:
            today = date.today()
            expiring_items = []
            
            for _, item in df.iterrows():
                if item["expire_date"] != "N/A":
                    try:
                        exp_date = date.fromisoformat(item["expire_date"])
                        days_until_expiry = (exp_date - today).days
                        if 0 <= days_until_expiry <= 7:
                            expiring_items.append({
                                "name": item["name"],
                                "quantity": item["quantity"],
                                "expire_date": item["expire_date"],
                                "days_left": days_until_expiry
                            })
                    except:
                        pass
            
            if expiring_items:
                st.markdown("---")
                st.error(f"🚨 {len(expiring_items)} items expiring within 7 days!")
                exp_df = pd.DataFrame(expiring_items)
                st.dataframe(exp_df, hide_index=True, use_container_width=True)
        
    finally:
        db.close()


def sql_runner_tab():
    """
    Display the SQL Runner tab for executing custom queries.
    """
    st.header("💻 SQL Query Runner")
    
    st.warning("⚠️ Be careful! This executes raw SQL queries directly on the database.")
    
    # SQL input
    sql_query = st.text_area(
        "Enter SQL Query",
        height=150,
        placeholder="SELECT * FROM items WHERE quantity > 10;",
        help="Enter a SQL query to execute against the inventory database"
    )
    
    # Example queries
    with st.expander("📝 Example Queries"):
        st.code("-- Get all items\nSELECT * FROM items;", language="sql")
        st.code("-- Get items by category\nSELECT * FROM items WHERE category = 'fruits';", language="sql")
        st.code("-- Get low stock items\nSELECT * FROM items WHERE quantity < 5;", language="sql")
        st.code("-- Get items expiring soon\nSELECT * FROM items WHERE expire_date <= date('now', '+7 days');", language="sql")
        st.code("-- Count items by category\nSELECT category, COUNT(*) as count FROM items GROUP BY category;", language="sql")
    
    # Execute button
    if st.button("▶️ Execute Query", type="primary"):
        if not sql_query.strip():
            st.error("❌ Please enter a SQL query")
            return
        
        db = get_db_session()
        
        try:
            # Execute query
            results = crud.execute_raw_sql(db, sql_query)
            
            if not results:
                st.success("✅ Query executed successfully (no results returned)")
                return
            
            # Display results
            st.success(f"✅ Query executed successfully! Retrieved {len(results)} rows.")
            
            # Convert to DataFrame
            df = pd.DataFrame(results)
            
            # Display results
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Download button
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download Results as CSV",
                data=csv,
                file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
        except Exception as e:
            st.error(f"❌ Error executing query: {str(e)}")
        
        finally:
            db.close()


def main():
    """
    Main dashboard application.
    """
    # Page configuration
    st.set_page_config(
        page_title="Inventory Dashboard",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize database
    init_db()
    
    # Check authentication
    if not check_authentication():
        login_page()
        return
    
    # Sidebar
    with st.sidebar:
        st.title("📦 Inventory System")
        st.markdown("---")
        
        # User info
        st.success("✅ Logged In")
        
        if st.button("🚪 Logout", use_container_width=True):
            logout()
        
        st.markdown("---")
        
        # System info
        st.subheader("ℹ️ System Information")
        st.text(f"Database: SQLite")
        st.text(f"FastAPI: Running")
        st.text(f"Version: 1.0.0")
        
        st.markdown("---")
        
        # Refresh button
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()
    
    # Main title
    st.title("📦 Voice-Managed Inventory Dashboard")
    st.markdown("Monitor and manage your inventory system")
    
    st.markdown("---")
    
    # Create tabs
    tab1, tab2 = st.tabs(["📊 Inventory", "💻 SQL Runner"])
    
    with tab1:
        inventory_tab()
    
    with tab2:
        sql_runner_tab()


if __name__ == "__main__":
    main()
