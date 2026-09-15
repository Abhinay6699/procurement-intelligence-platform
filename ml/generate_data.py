import pandas as pd
import numpy as np
import uuid
from datetime import datetime, timedelta
import random
import os

np.random.seed(42)
random.seed(42)

NUM_VENDORS = 50
NUM_CONTRACTS = 80
NUM_POS = 1500
NUM_INVOICES = 2000

LEAK_RATE = 0.08
APPROVAL_THRESHOLD = 10000

def generate_data():
    # 1. Vendors
    categories = ['IT Services', 'Office Supplies', 'Consulting', 'Logistics', 'Marketing']
    countries = ['US', 'UK', 'IN', 'CA', 'SG', 'RU', 'KP'] # RU, KP as high risk
    
    vendors = []
    for i in range(NUM_VENDORS):
        country = random.choice(countries)
        risk_tier = 'High' if country in ['RU', 'KP'] else random.choice(['Low', 'Medium'])
        vendors.append({
            'vendor_id': f"VEND{i:03d}",
            'name': f"Vendor_{i}",
            'category': random.choice(categories),
            'country': country,
            'risk_tier': risk_tier,
            'is_approved_vendor': True  # default, will be overridden below
        })
    df_vendors = pd.DataFrame(vendors)

    # 2. Contracts
    contracts = []
    for i in range(NUM_CONTRACTS):
        vendor = random.choice(vendors)
        contracts.append({
            'contract_id': f"CONT{i:04d}",
            'vendor_id': vendor['vendor_id'],
            'item_category': vendor['category'],
            'negotiated_rate': round(random.uniform(50, 500), 2),
            'valid_from': datetime(2023, 1, 1) + timedelta(days=random.randint(0, 100)),
            'valid_to': datetime(2024, 6, 1) + timedelta(days=random.randint(0, 200)) # Some expire early
        })
    df_contracts = pd.DataFrame(contracts)

    # Set vendor approval status based on contract presence
    contracted_vendor_ids = set(df_contracts['vendor_id'].unique())
    for v in vendors:
        if v['vendor_id'] in contracted_vendor_ids:
            v['is_approved_vendor'] = True
        else:
            # 40% of no-contract vendors are still approved (legitimate one-off suppliers)
            v['is_approved_vendor'] = random.random() < 0.4
    df_vendors = pd.DataFrame(vendors)

    # 3. Purchase Orders
    pos = []
    labels = []
    
    for vendor in vendors:
        current_date = datetime(2023, 6, 1)
        num_pos_for_vendor = random.randint(20, 40)
        
        for _ in range(num_pos_for_vendor):
            current_date += timedelta(days=random.randint(2, 15))
            if current_date > datetime(2024, 12, 31):
                break
                
            is_split = False
            is_maverick = False
            difficulty = 'easy'
            dept = random.choice(['IT', 'HR', 'Marketing', 'Finance', 'Operations'])
            
            # Check if contract exists
            v_contracts = df_contracts[df_contracts['vendor_id'] == vendor['vendor_id']]
            if v_contracts.empty:
                contract_rate = round(random.uniform(50, 500), 2)
                amount = round(contract_rate * random.randint(1, 20), 2)
                
                if vendor['is_approved_vendor']:
                    # Hard Negative: Approved vendor, no active contract — legitimate one-off purchase
                    is_maverick = False
                    difficulty = 'hard'
                else:
                    # Maverick spend: unapproved vendor, no contract
                    is_maverick = True
                    rand_val = random.random()
                    if rand_val < LEAK_RATE * 3:
                        # Hard Positive: small amount that looks like a harmless one-off
                        amount = round(random.uniform(50, 300), 2)
                        difficulty = 'hard'
                    else:
                        difficulty = 'easy'
            else:
                contract_rate = v_contracts.iloc[0]['negotiated_rate']
                amount = round(contract_rate * random.randint(10, 100), 2)
                if current_date > v_contracts.iloc[0]['valid_to']:
                    # Expired contract — still maverick (hard case for date-aware detectors)
                    is_maverick = True
                    difficulty = 'hard'
                else:
                    difficulty = 'easy'
            
            # Split PO logic (skip if already maverick to avoid label overlap)
            rand_split = random.random()
            if not is_maverick and rand_split < LEAK_RATE and APPROVAL_THRESHOLD < amount <= (APPROVAL_THRESHOLD * 2 - 600):
                # Split into two (Easy Positive)
                is_split = True
                amt1 = APPROVAL_THRESHOLD - random.randint(100, 500)
                amt2 = amount - amt1
                diff_split = 'easy'
            elif not is_maverick and rand_split < LEAK_RATE * 2:
                # Hard Positive: Total is barely over 10k, split into two pieces
                is_split = True
                amount = 10100 + random.randint(0, 150)
                amt1 = 5000 + random.randint(0, 50)
                amt2 = amount - amt1
                diff_split = 'hard'
                
            if is_split:
                po_id1 = f"PO{len(pos):05d}"
                pos.append({
                    'po_id': po_id1,
                    'vendor_id': vendor['vendor_id'],
                    'amount': amt1,
                    'created_at': current_date,
                    'status': 'Approved',
                    'department': dept
                })
                labels.append({'id': po_id1, 'type': 'po', 'leakage_type': 'Split PO', 'flag': 1, 'difficulty': diff_split})
                
                po_date2 = current_date + timedelta(days=random.randint(1, 3))
                po_id2 = f"PO{len(pos):05d}"
                pos.append({
                    'po_id': po_id2,
                    'vendor_id': vendor['vendor_id'],
                    'amount': amt2,
                    'created_at': po_date2,
                    'status': 'Approved',
                    'department': dept
                })
                labels.append({'id': po_id2, 'type': 'po', 'leakage_type': 'Split PO', 'flag': 1, 'difficulty': diff_split})
                
                current_date = po_date2 # Advance current date to avoid overlaps
                continue
            elif not is_maverick and random.random() < LEAK_RATE:
                # Hard Negative for Split PO: legitimate POs close together
                amt1 = round(random.uniform(3000, 9000), 2)
                amt2 = round(random.uniform(2000, 9000), 2)
                
                po_id1 = f"PO{len(pos):05d}"
                pos.append({
                    'po_id': po_id1,
                    'vendor_id': vendor['vendor_id'],
                    'amount': amt1,
                    'created_at': current_date,
                    'status': 'Approved',
                    'department': dept
                })
                # It's a legitimate PO
                labels.append({'id': po_id1, 'type': 'po', 'leakage_type': 'None', 'flag': 0, 'difficulty': 'hard'})
                
                po_date2 = current_date + timedelta(days=random.randint(1, 3))
                po_id2 = f"PO{len(pos):05d}"
                
                # Hard negative: different department!
                other_depts = [d for d in ['IT', 'HR', 'Marketing', 'Finance', 'Operations'] if d != dept]
                pos.append({
                    'po_id': po_id2,
                    'vendor_id': vendor['vendor_id'],
                    'amount': amt2,
                    'created_at': po_date2,
                    'status': 'Approved',
                    'department': random.choice(other_depts)
                })
                labels.append({'id': po_id2, 'type': 'po', 'leakage_type': 'None', 'flag': 0, 'difficulty': 'hard'})
                current_date = po_date2
                continue
    
            # Normal PO
            po_id = f"PO{len(pos):05d}"
            pos.append({
                'po_id': po_id,
                'vendor_id': vendor['vendor_id'],
                'amount': amount,
                'created_at': current_date,
                'status': 'Approved',
                'department': dept
            })
            
            if is_maverick:
                labels.append({'id': po_id, 'type': 'po', 'leakage_type': 'Maverick Spend', 'flag': 1, 'difficulty': difficulty})
            else:
                labels.append({'id': po_id, 'type': 'po', 'leakage_type': 'None', 'flag': 0, 'difficulty': difficulty})

    df_pos = pd.DataFrame(pos)

    # 4. Invoices
    invoices = []
    extra_pos = []
    
    for po in pos:
        invoice_date = po['created_at'] + timedelta(days=random.randint(5, 30))
        due_date = invoice_date + timedelta(days=30)
        
        amount = po['amount']
        is_price_leak = False
        is_dupe = False
        
        # Price leakage
        rand_price = random.random()
        if rand_price < LEAK_RATE:
            amount = round(amount * random.uniform(1.1, 1.5), 2)
            is_price_leak = True
            diff_price = 'easy'
        elif rand_price < LEAK_RATE * 2:
            # Hard Positive: 5.1% to 6.0% markup
            amount = round(amount * random.uniform(1.051, 1.06), 2)
            is_price_leak = True
            diff_price = 'hard'
        elif random.random() < LEAK_RATE:
            # Hard Negative: legitimate small variance below the 5% threshold
            amount = round(amount * random.uniform(1.01, 1.049), 2)
            diff_price = 'hard'
        else:
            diff_price = 'easy'
            
        inv_id = f"INV{len(invoices):05d}"
        invoices.append({
            'invoice_id': inv_id,
            'vendor_id': po['vendor_id'],
            'po_id': po['po_id'],
            'amount': amount,
            'invoice_date': invoice_date,
            'due_date': due_date,
            'status': 'Paid'
        })
        
        if is_price_leak:
            labels.append({'id': inv_id, 'type': 'invoice', 'leakage_type': 'Price Leakage', 'flag': 1, 'difficulty': diff_price})
        else:
            labels.append({'id': inv_id, 'type': 'invoice', 'leakage_type': 'None', 'flag': 0, 'difficulty': diff_price})
            
        # Duplicate invoice
        rand_dupe = random.random()
        if rand_dupe < LEAK_RATE and not is_price_leak:
            inv_id2 = f"INV{len(invoices):05d}"
            invoices.append({
                'invoice_id': inv_id2,
                'vendor_id': po['vendor_id'],
                'po_id': po['po_id'],
                'amount': amount, # Exact same amount
                'invoice_date': invoice_date + timedelta(days=random.randint(1, 3)),
                'due_date': due_date,
                'status': 'Paid'
            })
            labels.append({'id': inv_id2, 'type': 'invoice', 'leakage_type': 'Duplicate Invoice', 'flag': 1, 'difficulty': 'easy'})
        elif rand_dupe < LEAK_RATE * 2 and not is_price_leak:
            # Hard Positive: amounts differ by just over $1.00 (tax diff)
            inv_id2 = f"INV{len(invoices):05d}"
            invoices.append({
                'invoice_id': inv_id2,
                'vendor_id': po['vendor_id'],
                'po_id': po['po_id'],
                'amount': round(amount + random.uniform(1.5, 3.0), 2),
                'invoice_date': invoice_date + timedelta(days=random.randint(0, 1)),
                'due_date': due_date,
                'status': 'Paid'
            })
            labels.append({'id': inv_id2, 'type': 'invoice', 'leakage_type': 'Duplicate Invoice', 'flag': 1, 'difficulty': 'hard'})
            
        # Hard Negative for Duplicate Invoice
        if random.random() < LEAK_RATE and not is_price_leak:
            po_id_hn = f"PO_HN_{len(extra_pos)}"
            extra_pos.append({
                'po_id': po_id_hn,
                'vendor_id': po['vendor_id'],
                'amount': amount,
                'created_at': po['created_at'],
                'status': 'Approved',
                'department': random.choice(['IT', 'HR', 'Marketing', 'Finance', 'Operations'])
            })
            labels.append({'id': po_id_hn, 'type': 'po', 'leakage_type': 'None', 'flag': 0, 'difficulty': 'hard'})
            
            inv_id_hn = f"INV_HN_{len(extra_pos)}"
            invoices.append({
                'invoice_id': inv_id_hn,
                'vendor_id': po['vendor_id'],
                'po_id': po_id_hn,
                'amount': amount, # Exact same amount
                'invoice_date': invoice_date + timedelta(days=random.randint(0, 2)),
                'due_date': due_date,
                'status': 'Paid'
            })
            labels.append({'id': inv_id_hn, 'type': 'invoice', 'leakage_type': 'None', 'flag': 0, 'difficulty': 'hard'})
            
    pos.extend(extra_pos)
    df_pos = pd.DataFrame(pos)
    df_invoices = pd.DataFrame(invoices)

    # 5. Payments
    payments = []
    for idx, row in df_invoices.iterrows():
        payment_date = row['due_date'] - timedelta(days=random.randint(-15, 15))
        discount_taken = 0.0
        is_payment_leak = False
        
        # Payment leakage
        rand_pay = random.random()
        if payment_date > row['due_date']:
            # Late payment
            if rand_pay < LEAK_RATE:
                # Took discount anyway (leakage) (Easy Positive)
                discount_taken = round(row['amount'] * 0.02, 2)
                is_payment_leak = True
                diff_pay = 'easy'
            elif rand_pay < LEAK_RATE * 2:
                # Hard Positive: paid exactly 1 day late, and took discount
                payment_date = row['due_date'] + timedelta(days=1)
                discount_taken = round(row['amount'] * 0.02, 2)
                is_payment_leak = True
                diff_pay = 'hard'
            else:
                diff_pay = 'easy'
        elif payment_date == row['due_date']:
            # Hard Negative: paid exactly on due date, legitimately took discount
            if random.random() < LEAK_RATE:
                discount_taken = round(row['amount'] * 0.02, 2)
                diff_pay = 'hard'
            else:
                diff_pay = 'easy'
        elif payment_date < row['due_date']:
            # Early payment: legitimately take discount
            if random.random() < 0.5:
                discount_taken = round(row['amount'] * 0.02, 2)
            diff_pay = 'easy'
        else:
            diff_pay = 'easy'
        
        pay_id = f"PAY{len(payments):05d}"
        payments.append({
            'payment_id': pay_id,
            'invoice_id': row['invoice_id'],
            'amount_paid': row['amount'] - discount_taken,
            'payment_date': payment_date,
            'discount_taken': discount_taken
        })
        
        if is_payment_leak:
            labels.append({'id': pay_id, 'type': 'payment', 'leakage_type': 'Payment Leakage', 'flag': 1, 'difficulty': diff_pay})
        else:
            labels.append({'id': pay_id, 'type': 'payment', 'leakage_type': 'None', 'flag': 0, 'difficulty': diff_pay})
            
    df_payments = pd.DataFrame(payments)
    df_labels = pd.DataFrame(labels)
    
    # Save to data directory
    os.makedirs('data/synthetic', exist_ok=True)
    df_vendors.to_csv('data/synthetic/vendors.csv', index=False)
    df_contracts.to_csv('data/synthetic/contracts.csv', index=False)
    df_pos.to_csv('data/synthetic/purchase_orders.csv', index=False)
    df_invoices.to_csv('data/synthetic/invoices.csv', index=False)
    df_payments.to_csv('data/synthetic/payments.csv', index=False)
    df_labels.to_csv('data/synthetic/ground_truth.csv', index=False)
    
    print(f"Generated {len(df_vendors)} vendors, {len(df_contracts)} contracts, {len(df_pos)} POs, {len(df_invoices)} invoices, {len(df_payments)} payments.")
    print(f"Leakage breakdown:\n{df_labels[df_labels['flag'] == 1]['leakage_type'].value_counts()}")

if __name__ == "__main__":
    generate_data()
