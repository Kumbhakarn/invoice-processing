# Invoice extraction evaluation report

- Documents evaluated: 10
- Fields evaluated: 279
- Correct fields: 0
- Incorrect fields: 279
- Missing extracted values: 279
- Field completeness: 0.0%
- Unexpected non-null values: 0
- Actual files without expected references: 0
- Exact field matches: 0
- Normalized text matches: 0
- Normalized date matches: 0
- Numeric tolerance matches: 0
- Field accuracy: 0.0%
- Line-item count correct: 0/10
- Line-item field accuracy: 0.0%

## Per document

| Document | Correct / fields | Accuracy | Line items (matched / expected; actual) |
|---|---:|---:|---:|
| inv-01 | 0 / 28 | 0.0% | 0 / 2; missing |
| inv-02 | 0 / 29 | 0.0% | 0 / 3; missing |
| inv-03 | 0 / 27 | 0.0% | 0 / 1; missing |
| inv-04 | 0 / 28 | 0.0% | 0 / 2; missing |
| inv-05 | 0 / 28 | 0.0% | 0 / 2; missing |
| inv-06 | 0 / 28 | 0.0% | 0 / 2; missing |
| inv-07 | 0 / 28 | 0.0% | 0 / 2; missing |
| inv-08 | 0 / 28 | 0.0% | 0 / 2; missing |
| inv-09 | 0 / 27 | 0.0% | 0 / 1; missing |
| inv-10 | 0 / 28 | 0.0% | 0 / 2; missing |

## Incorrect fields

### inv-01
- `amount_in_words`: expected `None`, actual `None`
- `buyer_address`: expected `'48 Bridge Road, Bristol BS1 4QA, United Kingdom'`, actual `None`
- `buyer_name`: expected `'Greenfield Design Studio'`, actual `None`
- `consignee_address`: expected `None`, actual `None`
- `consignee_name`: expected `None`, actual `None`
- `country_of_final_destination`: expected `None`, actual `None`
- `country_of_origin`: expected `None`, actual `None`
- `currency`: expected `'GBP'`, actual `None`
- `document_type`: expected `'invoice'`, actual `None`
- `exporter_address`: expected `'12 King Street, Manchester M2 6AB, United Kingdom'`, actual `None`
- `exporter_name`: expected `'Northstar Office Supply Ltd.'`, actual `None`
- `final_destination`: expected `None`, actual `None`
- `gross_weight`: expected `None`, actual `None`
- `incoterms`: expected `None`, actual `None`
- `invoice_date`: expected `'2025-01-14'`, actual `None`
- `invoice_number`: expected `'NS-1048'`, actual `None`
- `net_weight`: expected `None`, actual `None`
- `notify_party_address`: expected `None`, actual `None`
- `notify_party_name`: expected `None`, actual `None`
- `payment_terms`: expected `'Net 30'`, actual `None`
- `port_of_discharge`: expected `None`, actual `None`
- `port_of_loading`: expected `None`, actual `None`
- `shipping_marks`: expected `None`, actual `None`
- `terms_of_delivery_and_payment`: expected `'Net 30'`, actual `None`
- `weight_unit`: expected `None`, actual `None`
- `line_items`: expected `[{'sr_no': 1, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'A4 recycled paper', 'quantity': 10, 'hsn_code': None, 'unit_of_measurement': 'reams', 'rate': 4.5, 'amount': 45.0}, {'sr_no': 2, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Blue toner cartridge', 'quantity': 2, 'hsn_code': None, 'unit_of_measurement': 'each', 'rate': 38.0, 'amount': 76.0}]`, actual `None`
- `line_items[0]`: expected `{'sr_no': 1, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'A4 recycled paper', 'quantity': 10, 'hsn_code': None, 'unit_of_measurement': 'reams', 'rate': 4.5, 'amount': 45.0}`, actual `None`
- `line_items[1]`: expected `{'sr_no': 2, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Blue toner cartridge', 'quantity': 2, 'hsn_code': None, 'unit_of_measurement': 'each', 'rate': 38.0, 'amount': 76.0}`, actual `None`

### inv-02
- `amount_in_words`: expected `None`, actual `None`
- `buyer_address`: expected `'220 Collins St, Melbourne VIC 3000, Australia'`, actual `None`
- `buyer_name`: expected `'Redgum Robotics'`, actual `None`
- `consignee_address`: expected `None`, actual `None`
- `consignee_name`: expected `None`, actual `None`
- `country_of_final_destination`: expected `None`, actual `None`
- `country_of_origin`: expected `None`, actual `None`
- `currency`: expected `'AUD'`, actual `None`
- `document_type`: expected `'tax invoice'`, actual `None`
- `exporter_address`: expected `'7 Harbour Rd, Fremantle WA 6160, Australia'`, actual `None`
- `exporter_name`: expected `'Pacific Components Pty Ltd'`, actual `None`
- `final_destination`: expected `None`, actual `None`
- `gross_weight`: expected `None`, actual `None`
- `incoterms`: expected `None`, actual `None`
- `invoice_date`: expected `'03/02/2025'`, actual `None`
- `invoice_number`: expected `'PC/25/0081'`, actual `None`
- `net_weight`: expected `None`, actual `None`
- `notify_party_address`: expected `None`, actual `None`
- `notify_party_name`: expected `None`, actual `None`
- `payment_terms`: expected `'due 14 days'`, actual `None`
- `port_of_discharge`: expected `None`, actual `None`
- `port_of_loading`: expected `None`, actual `None`
- `shipping_marks`: expected `None`, actual `None`
- `terms_of_delivery_and_payment`: expected `'due 14 days'`, actual `None`
- `weight_unit`: expected `None`, actual `None`
- `line_items`: expected `[{'sr_no': 1, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Sensor module PX', 'quantity': 4, 'hsn_code': None, 'unit_of_measurement': None, 'rate': 125.5, 'amount': 502.0}, {'sr_no': 2, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Cable harness', 'quantity': 8, 'hsn_code': None, 'unit_of_measurement': None, 'rate': 18.75, 'amount': 150.0}, {'sr_no': 3, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Packing', 'quantity': 1, 'hsn_code': None, 'unit_of_measurement': None, 'rate': 12.0, 'amount': 12.0}]`, actual `None`
- `line_items[0]`: expected `{'sr_no': 1, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Sensor module PX', 'quantity': 4, 'hsn_code': None, 'unit_of_measurement': None, 'rate': 125.5, 'amount': 502.0}`, actual `None`
- `line_items[1]`: expected `{'sr_no': 2, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Cable harness', 'quantity': 8, 'hsn_code': None, 'unit_of_measurement': None, 'rate': 18.75, 'amount': 150.0}`, actual `None`
- `line_items[2]`: expected `{'sr_no': 3, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Packing', 'quantity': 1, 'hsn_code': None, 'unit_of_measurement': None, 'rate': 12.0, 'amount': 12.0}`, actual `None`

### inv-03
- `amount_in_words`: expected `'Two thousand one hundred sixty euros only'`, actual `None`
- `buyer_address`: expected `'18 rue des Fleurs, 69002 Lyon, France'`, actual `None`
- `buyer_name`: expected `'Maison du Lin SARL'`, actual `None`
- `consignee_address`: expected `'18 rue des Fleurs, 69002 Lyon, France'`, actual `None`
- `consignee_name`: expected `'Maison du Lin SARL'`, actual `None`
- `country_of_final_destination`: expected `'France'`, actual `None`
- `country_of_origin`: expected `'India'`, actual `None`
- `currency`: expected `'EUR'`, actual `None`
- `document_type`: expected `'commercial invoice - export'`, actual `None`
- `exporter_address`: expected `'44 Ring Road, Surat 395002, Gujarat, India'`, actual `None`
- `exporter_name`: expected `'Saffron Looms Pvt. Ltd.'`, actual `None`
- `final_destination`: expected `'France'`, actual `None`
- `gross_weight`: expected `96`, actual `None`
- `incoterms`: expected `'FOB'`, actual `None`
- `invoice_date`: expected `'14 March 2025'`, actual `None`
- `invoice_number`: expected `'EX-7719'`, actual `None`
- `net_weight`: expected `84`, actual `None`
- `notify_party_address`: expected `None`, actual `None`
- `notify_party_name`: expected `None`, actual `None`
- `payment_terms`: expected `'30% advance, balance against documents'`, actual `None`
- `port_of_discharge`: expected `'Marseille, France'`, actual `None`
- `port_of_loading`: expected `'Nhava Sheva, India'`, actual `None`
- `shipping_marks`: expected `'MDL / LYON / 01-06'`, actual `None`
- `terms_of_delivery_and_payment`: expected `'FOB Nhava Sheva; 30% advance, balance against documents'`, actual `None`
- `weight_unit`: expected `'kg'`, actual `None`
- `line_items`: expected `[{'sr_no': 1, 'marks_and_numbers': None, 'number_of_packages': 6, 'description_of_goods': 'Linen tablecloths', 'quantity': 120, 'hsn_code': None, 'unit_of_measurement': 'pcs', 'rate': 18.0, 'amount': 2160.0}]`, actual `None`
- `line_items[0]`: expected `{'sr_no': 1, 'marks_and_numbers': None, 'number_of_packages': 6, 'description_of_goods': 'Linen tablecloths', 'quantity': 120, 'hsn_code': None, 'unit_of_measurement': 'pcs', 'rate': 18.0, 'amount': 2160.0}`, actual `None`

### inv-04
- `amount_in_words`: expected `None`, actual `None`
- `buyer_address`: expected `'Industriestrasse 9, 6020 Innsbruck, Austria'`, actual `None`
- `buyer_name`: expected `'Alpine Works GmbH'`, actual `None`
- `consignee_address`: expected `None`, actual `None`
- `consignee_name`: expected `None`, actual `None`
- `country_of_final_destination`: expected `None`, actual `None`
- `country_of_origin`: expected `None`, actual `None`
- `currency`: expected `'USD'`, actual `None`
- `document_type`: expected `'invoice'`, actual `None`
- `exporter_address`: expected `'500 Market Street, Suite 210, San Francisco, CA 94105, USA'`, actual `None`
- `exporter_name`: expected `'Blue Peak Industrial Inc.'`, actual `None`
- `final_destination`: expected `None`, actual `None`
- `gross_weight`: expected `None`, actual `None`
- `incoterms`: expected `None`, actual `None`
- `invoice_date`: expected `'2025/04/06'`, actual `None`
- `invoice_number`: expected `'BPI-9002'`, actual `None`
- `net_weight`: expected `None`, actual `None`
- `notify_party_address`: expected `None`, actual `None`
- `notify_party_name`: expected `None`, actual `None`
- `payment_terms`: expected `'Due on receipt'`, actual `None`
- `port_of_discharge`: expected `None`, actual `None`
- `port_of_loading`: expected `None`, actual `None`
- `shipping_marks`: expected `None`, actual `None`
- `terms_of_delivery_and_payment`: expected `'Due on receipt'`, actual `None`
- `weight_unit`: expected `None`, actual `None`
- `line_items`: expected `[{'sr_no': 1, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Steel fasteners, grade A', 'quantity': 1000, 'hsn_code': None, 'unit_of_measurement': 'pcs', 'rate': 0.08, 'amount': 80.0}, {'sr_no': 2, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Freight', 'quantity': 1, 'hsn_code': None, 'unit_of_measurement': 'lot', 'rate': 22.5, 'amount': 22.5}]`, actual `None`
- `line_items[0]`: expected `{'sr_no': 1, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Steel fasteners, grade A', 'quantity': 1000, 'hsn_code': None, 'unit_of_measurement': 'pcs', 'rate': 0.08, 'amount': 80.0}`, actual `None`
- `line_items[1]`: expected `{'sr_no': 2, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Freight', 'quantity': 1, 'hsn_code': None, 'unit_of_measurement': 'lot', 'rate': 22.5, 'amount': 22.5}`, actual `None`

### inv-05
- `amount_in_words`: expected `None`, actual `None`
- `buyer_address`: expected `'90 Queen Street, Auckland 1010, New Zealand'`, actual `None`
- `buyer_name`: expected `'Cedar House Imports'`, actual `None`
- `consignee_address`: expected `None`, actual `None`
- `consignee_name`: expected `None`, actual `None`
- `country_of_final_destination`: expected `None`, actual `None`
- `country_of_origin`: expected `None`, actual `None`
- `currency`: expected `'JPY'`, actual `None`
- `document_type`: expected `'invoice'`, actual `None`
- `exporter_address`: expected `'2-8-1 Marunouchi, Chiyoda-ku, Tokyo 100-0005, Japan'`, actual `None`
- `exporter_name`: expected `'Hikari Trading Co.'`, actual `None`
- `final_destination`: expected `None`, actual `None`
- `gross_weight`: expected `None`, actual `None`
- `incoterms`: expected `None`, actual `None`
- `invoice_date`: expected `'2025年5月8日'`, actual `None`
- `invoice_number`: expected `'HT-2025-311'`, actual `None`
- `net_weight`: expected `None`, actual `None`
- `notify_party_address`: expected `None`, actual `None`
- `notify_party_name`: expected `None`, actual `None`
- `payment_terms`: expected `'Bank transfer within 20 days'`, actual `None`
- `port_of_discharge`: expected `None`, actual `None`
- `port_of_loading`: expected `None`, actual `None`
- `shipping_marks`: expected `None`, actual `None`
- `terms_of_delivery_and_payment`: expected `'Bank transfer within 20 days'`, actual `None`
- `weight_unit`: expected `None`, actual `None`
- `line_items`: expected `[{'sr_no': 1, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Ceramic tea set', 'quantity': 15, 'hsn_code': None, 'unit_of_measurement': 'sets', 'rate': 3200, 'amount': 48000}, {'sr_no': 2, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Gift box', 'quantity': 15, 'hsn_code': None, 'unit_of_measurement': 'pieces', 'rate': 250, 'amount': 3750}]`, actual `None`
- `line_items[0]`: expected `{'sr_no': 1, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Ceramic tea set', 'quantity': 15, 'hsn_code': None, 'unit_of_measurement': 'sets', 'rate': 3200, 'amount': 48000}`, actual `None`
- `line_items[1]`: expected `{'sr_no': 2, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Gift box', 'quantity': 15, 'hsn_code': None, 'unit_of_measurement': 'pieces', 'rate': 250, 'amount': 3750}`, actual `None`

### inv-06
- `amount_in_words`: expected `None`, actual `None`
- `buyer_address`: expected `'8 Water St, Halifax, NS B3H 1A1, Canada'`, actual `None`
- `buyer_name`: expected `'Harborview Cafe'`, actual `None`
- `consignee_address`: expected `None`, actual `None`
- `consignee_name`: expected `None`, actual `None`
- `country_of_final_destination`: expected `None`, actual `None`
- `country_of_origin`: expected `None`, actual `None`
- `currency`: expected `'CAD'`, actual `None`
- `document_type`: expected `'invoice'`, actual `None`
- `exporter_address`: expected `'31 Wellington Ave, Ottawa, ON K1A 0B1, Canada'`, actual `None`
- `exporter_name`: expected `'Maple Kitchen Tools'`, actual `None`
- `final_destination`: expected `None`, actual `None`
- `gross_weight`: expected `None`, actual `None`
- `incoterms`: expected `None`, actual `None`
- `invoice_date`: expected `'06/07/25'`, actual `None`
- `invoice_number`: expected `'MKT-5560'`, actual `None`
- `net_weight`: expected `None`, actual `None`
- `notify_party_address`: expected `None`, actual `None`
- `notify_party_name`: expected `None`, actual `None`
- `payment_terms`: expected `None`, actual `None`
- `port_of_discharge`: expected `None`, actual `None`
- `port_of_loading`: expected `None`, actual `None`
- `shipping_marks`: expected `None`, actual `None`
- `terms_of_delivery_and_payment`: expected `None`, actual `None`
- `weight_unit`: expected `None`, actual `None`
- `line_items`: expected `[{'sr_no': 1, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Stainless mixing bowl', 'quantity': 6, 'hsn_code': None, 'unit_of_measurement': 'each', 'rate': 14.25, 'amount': 85.5}, {'sr_no': 2, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Wooden spoon set', 'quantity': 3, 'hsn_code': None, 'unit_of_measurement': 'sets', 'rate': 9.0, 'amount': 27.0}]`, actual `None`
- `line_items[0]`: expected `{'sr_no': 1, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Stainless mixing bowl', 'quantity': 6, 'hsn_code': None, 'unit_of_measurement': 'each', 'rate': 14.25, 'amount': 85.5}`, actual `None`
- `line_items[1]`: expected `{'sr_no': 2, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Wooden spoon set', 'quantity': 3, 'hsn_code': None, 'unit_of_measurement': 'sets', 'rate': 9.0, 'amount': 27.0}`, actual `None`

### inv-07
- `amount_in_words`: expected `'Four thousand eight hundred fifteen US dollars only'`, actual `None`
- `buyer_address`: expected `'15 Tuas View Place, Singapore 637431'`, actual `None`
- `buyer_name`: expected `'Sunline Marine Pte Ltd'`, actual `None`
- `consignee_address`: expected `'15 Tuas View Place, Singapore 637431'`, actual `None`
- `consignee_name`: expected `'Sunline Marine Pte Ltd'`, actual `None`
- `country_of_final_destination`: expected `'Singapore'`, actual `None`
- `country_of_origin`: expected `'United Arab Emirates'`, actual `None`
- `currency`: expected `'USD'`, actual `None`
- `document_type`: expected `'commercial invoice'`, actual `None`
- `exporter_address`: expected `'Warehouse 4, Jebel Ali Industrial Area, Dubai, United Arab Emirates'`, actual `None`
- `exporter_name`: expected `'Orbit Parts Manufacturing LLC'`, actual `None`
- `final_destination`: expected `'Singapore'`, actual `None`
- `gross_weight`: expected `820`, actual `None`
- `incoterms`: expected `'CIF'`, actual `None`
- `invoice_date`: expected `'2025-08-19'`, actual `None`
- `invoice_number`: expected `'ORB-EX-440'`, actual `None`
- `net_weight`: expected `740`, actual `None`
- `notify_party_address`: expected `'15 Tuas View Place, Singapore 637431'`, actual `None`
- `notify_party_name`: expected `'Same as consignee'`, actual `None`
- `payment_terms`: expected `'60 days from invoice'`, actual `None`
- `port_of_discharge`: expected `'Singapore'`, actual `None`
- `port_of_loading`: expected `'Jebel Ali'`, actual `None`
- `shipping_marks`: expected `'SL / SINGAPORE'`, actual `None`
- `terms_of_delivery_and_payment`: expected `'CIF Singapore; 60 days from invoice'`, actual `None`
- `weight_unit`: expected `'kg'`, actual `None`
- `line_items`: expected `[{'sr_no': 1, 'marks_and_numbers': None, 'number_of_packages': 3, 'description_of_goods': 'Marine pump assembly', 'quantity': 3, 'hsn_code': None, 'unit_of_measurement': 'units', 'rate': 1450.0, 'amount': 4350.0}, {'sr_no': 2, 'marks_and_numbers': None, 'number_of_packages': 9, 'description_of_goods': 'Replacement seal kit', 'quantity': 9, 'hsn_code': None, 'unit_of_measurement': 'sets', 'rate': 85.0, 'amount': 765.0}]`, actual `None`
- `line_items[0]`: expected `{'sr_no': 1, 'marks_and_numbers': None, 'number_of_packages': 3, 'description_of_goods': 'Marine pump assembly', 'quantity': 3, 'hsn_code': None, 'unit_of_measurement': 'units', 'rate': 1450.0, 'amount': 4350.0}`, actual `None`
- `line_items[1]`: expected `{'sr_no': 2, 'marks_and_numbers': None, 'number_of_packages': 9, 'description_of_goods': 'Replacement seal kit', 'quantity': 9, 'hsn_code': None, 'unit_of_measurement': 'sets', 'rate': 85.0, 'amount': 765.0}`, actual `None`

### inv-08
- `amount_in_words`: expected `None`, actual `None`
- `buyer_address`: expected `'4 Station Road, York YO1 6AA, UK'`, actual `None`
- `buyer_name`: expected `'Mill House Cafe'`, actual `None`
- `consignee_address`: expected `None`, actual `None`
- `consignee_name`: expected `None`, actual `None`
- `country_of_final_destination`: expected `None`, actual `None`
- `country_of_origin`: expected `None`, actual `None`
- `currency`: expected `'GBP'`, actual `None`
- `document_type`: expected `'invoice'`, actual `None`
- `exporter_address`: expected `None`, actual `None`
- `exporter_name`: expected `'Cedar & Stone Bakery Supply'`, actual `None`
- `final_destination`: expected `None`, actual `None`
- `gross_weight`: expected `None`, actual `None`
- `incoterms`: expected `None`, actual `None`
- `invoice_date`: expected `'9 Sep 2025'`, actual `None`
- `invoice_number`: expected `'CS-208'`, actual `None`
- `net_weight`: expected `None`, actual `None`
- `notify_party_address`: expected `None`, actual `None`
- `notify_party_name`: expected `None`, actual `None`
- `payment_terms`: expected `None`, actual `None`
- `port_of_discharge`: expected `None`, actual `None`
- `port_of_loading`: expected `None`, actual `None`
- `shipping_marks`: expected `None`, actual `None`
- `terms_of_delivery_and_payment`: expected `None`, actual `None`
- `weight_unit`: expected `None`, actual `None`
- `line_items`: expected `[{'sr_no': 1, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Flour sacks', 'quantity': 5, 'hsn_code': None, 'unit_of_measurement': 'sacks', 'rate': 12.0, 'amount': 60.0}, {'sr_no': 2, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': None, 'quantity': None, 'hsn_code': None, 'unit_of_measurement': None, 'rate': None, 'amount': None}]`, actual `None`
- `line_items[0]`: expected `{'sr_no': 1, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Flour sacks', 'quantity': 5, 'hsn_code': None, 'unit_of_measurement': 'sacks', 'rate': 12.0, 'amount': 60.0}`, actual `None`
- `line_items[1]`: expected `{'sr_no': 2, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': None, 'quantity': None, 'hsn_code': None, 'unit_of_measurement': None, 'rate': None, 'amount': None}`, actual `None`

### inv-09
- `amount_in_words`: expected `None`, actual `None`
- `buyer_address`: expected `'100 Main St, Winnipeg, MB R3C 1A5, Canada'`, actual `None`
- `buyer_name`: expected `'Prairie Foods Inc.'`, actual `None`
- `consignee_address`: expected `None`, actual `None`
- `consignee_name`: expected `None`, actual `None`
- `country_of_final_destination`: expected `'Canada'`, actual `None`
- `country_of_origin`: expected `'UK'`, actual `None`
- `currency`: expected `'CAD'`, actual `None`
- `document_type`: expected `'commercial invoice - export'`, actual `None`
- `exporter_address`: expected `'6 Mill Road, Canterbury CT1 2AA, UK'`, actual `None`
- `exporter_name`: expected `'Riverbend Agri Exports Ltd.'`, actual `None`
- `final_destination`: expected `None`, actual `None`
- `gross_weight`: expected `10240`, actual `None`
- `incoterms`: expected `None`, actual `None`
- `invoice_date`: expected `'2025-10-02'`, actual `None`
- `invoice_number`: expected `'RA-1009'`, actual `None`
- `net_weight`: expected `10000`, actual `None`
- `notify_party_address`: expected `None`, actual `None`
- `notify_party_name`: expected `None`, actual `None`
- `payment_terms`: expected `'CAD 12,400 payable at sight'`, actual `None`
- `port_of_discharge`: expected `'Port of Montreal'`, actual `None`
- `port_of_loading`: expected `'Port of Felixstowe'`, actual `None`
- `shipping_marks`: expected `'PFI / WINNIPEG / LOT 9'`, actual `None`
- `terms_of_delivery_and_payment`: expected `'CAD 12,400 payable at sight'`, actual `None`
- `weight_unit`: expected `'kg'`, actual `None`
- `line_items`: expected `[{'sr_no': 1, 'marks_and_numbers': None, 'number_of_packages': 400, 'description_of_goods': 'Dried lentils', 'quantity': 400, 'hsn_code': None, 'unit_of_measurement': 'bags', 'rate': 31.0, 'amount': 12400.0}]`, actual `None`
- `line_items[0]`: expected `{'sr_no': 1, 'marks_and_numbers': None, 'number_of_packages': 400, 'description_of_goods': 'Dried lentils', 'quantity': 400, 'hsn_code': None, 'unit_of_measurement': 'bags', 'rate': 31.0, 'amount': 12400.0}`, actual `None`

### inv-10
- `amount_in_words`: expected `None`, actual `None`
- `buyer_address`: expected `'Am Sandtorkai 55, 20457 Hamburg, Germany'`, actual `None`
- `buyer_name`: expected `'Nordlicht Forschung GmbH'`, actual `None`
- `consignee_address`: expected `None`, actual `None`
- `consignee_name`: expected `None`, actual `None`
- `country_of_final_destination`: expected `None`, actual `None`
- `country_of_origin`: expected `None`, actual `None`
- `currency`: expected `'CHF'`, actual `None`
- `document_type`: expected `'invoice'`, actual `None`
- `exporter_address`: expected `'Seestrasse 21, 8002 Zürich, Switzerland'`, actual `None`
- `exporter_name`: expected `'Lumen Labs AG'`, actual `None`
- `final_destination`: expected `None`, actual `None`
- `gross_weight`: expected `None`, actual `None`
- `incoterms`: expected `None`, actual `None`
- `invoice_date`: expected `'11.03.2025'`, actual `None`
- `invoice_number`: expected `'LL-88'`, actual `None`
- `net_weight`: expected `None`, actual `None`
- `notify_party_address`: expected `None`, actual `None`
- `notify_party_name`: expected `None`, actual `None`
- `payment_terms`: expected `'15 days'`, actual `None`
- `port_of_discharge`: expected `None`, actual `None`
- `port_of_loading`: expected `None`, actual `None`
- `shipping_marks`: expected `None`, actual `None`
- `terms_of_delivery_and_payment`: expected `'15 days'`, actual `None`
- `weight_unit`: expected `None`, actual `None`
- `line_items`: expected `[{'sr_no': 1, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Optical calibration unit', 'quantity': 2, 'hsn_code': None, 'unit_of_measurement': 'units', 'rate': 725.0, 'amount': 1450.0}, {'sr_no': 2, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Calibration certificate', 'quantity': 2, 'hsn_code': None, 'unit_of_measurement': 'documents', 'rate': 40.0, 'amount': 80.0}]`, actual `None`
- `line_items[0]`: expected `{'sr_no': 1, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Optical calibration unit', 'quantity': 2, 'hsn_code': None, 'unit_of_measurement': 'units', 'rate': 725.0, 'amount': 1450.0}`, actual `None`
- `line_items[1]`: expected `{'sr_no': 2, 'marks_and_numbers': None, 'number_of_packages': None, 'description_of_goods': 'Calibration certificate', 'quantity': 2, 'hsn_code': None, 'unit_of_measurement': 'documents', 'rate': 40.0, 'amount': 80.0}`, actual `None`
