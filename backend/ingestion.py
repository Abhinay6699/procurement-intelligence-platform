import pandas as pd
from sqlalchemy.orm import Session
from . import models, schemas
from .database import engine, SessionLocal
import os
import datetime

def ingest_data():
    db = SessionLocal()
    try:
        # Check if already ingested
        if db.query(models.Vendor).first():
            print("Data already exists in the database. Skipping ingestion.")
            return

        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'synthetic')
        
        # 1. Vendors
        vendors_df = pd.read_csv(os.path.join(data_dir, 'vendors.csv'))
        for _, row in vendors_df.iterrows():
            vendor = models.Vendor(
                vendor_id=row['vendor_id'],
                name=row['name'],
                category=row['category'],
                country=row['country'],
                risk_tier=row['risk_tier']
            )
            db.add(vendor)
        db.commit()
        
        # Mapping vendor_id string to DB integer ID
        vendors = db.query(models.Vendor).all()
        vendor_map = {v.vendor_id: v.id for v in vendors}
        
        # 2. Contracts
        contracts_df = pd.read_csv(os.path.join(data_dir, 'contracts.csv'))
        for _, row in contracts_df.iterrows():
            contract = models.Contract(
                contract_id=row['contract_id'],
                vendor_id=vendor_map[row['vendor_id']],
                item_category=row['item_category'],
                negotiated_rate=row['negotiated_rate'],
                valid_from=datetime.datetime.strptime(row['valid_from'].split(' ')[0], '%Y-%m-%d'),
                valid_to=datetime.datetime.strptime(row['valid_to'].split(' ')[0], '%Y-%m-%d')
            )
            db.add(contract)
        db.commit()

        # 3. POs
        pos_df = pd.read_csv(os.path.join(data_dir, 'purchase_orders.csv'))
        for _, row in pos_df.iterrows():
            po = models.PurchaseOrder(
                po_id=row['po_id'],
                vendor_id=vendor_map[row['vendor_id']],
                amount=row['amount'],
                status=row['status'],
                created_at=datetime.datetime.strptime(row['created_at'].split(' ')[0], '%Y-%m-%d')
            )
            db.add(po)
        db.commit()

        pos = db.query(models.PurchaseOrder).all()
        po_map = {po.po_id: po.id for po in pos}
        
        # 4. Invoices
        invoices_df = pd.read_csv(os.path.join(data_dir, 'invoices.csv'))
        for _, row in invoices_df.iterrows():
            invoice = models.Invoice(
                invoice_id=row['invoice_id'],
                vendor_id=vendor_map[row['vendor_id']],
                po_id=po_map.get(row['po_id']),
                amount=row['amount'],
                invoice_date=datetime.datetime.strptime(row['invoice_date'].split(' ')[0], '%Y-%m-%d'),
                due_date=datetime.datetime.strptime(row['due_date'].split(' ')[0], '%Y-%m-%d'),
                status=row['status']
            )
            db.add(invoice)
        db.commit()

        invoices = db.query(models.Invoice).all()
        inv_map = {inv.invoice_id: inv.id for inv in invoices}

        # 5. Payments
        payments_df = pd.read_csv(os.path.join(data_dir, 'payments.csv'))
        for _, row in payments_df.iterrows():
            payment = models.Payment(
                payment_id=row['payment_id'],
                invoice_id=inv_map[row['invoice_id']],
                amount_paid=row['amount_paid'],
                payment_date=datetime.datetime.strptime(row['payment_date'].split(' ')[0], '%Y-%m-%d'),
                discount_taken=row['discount_taken']
            )
            db.add(payment)
        db.commit()
        
        print("Successfully ingested all synthetic data into the database.")
    except Exception as e:
        print(f"Error ingesting data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    ingest_data()
