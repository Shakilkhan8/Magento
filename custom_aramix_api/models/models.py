# -*- coding: utf-8 -*-
import base64
import datetime
import json

import requests
from odoo import models, fields, api


class CustomProductSend(models.Model):
    _inherit = 'product.template'

    def sync_product_data(self):
        url = "https://cportal.infor.aramex.com/WS_EDI_TEST_V02/RestService_API/SKU/ImportSKUs"
        all_products = self.env['product.template'].search([])
        list_of_products = []
        for product in all_products:
            if product.name and product.default_code:
                single_prod_data = {
                    "Description": product.name,
                    "Facility": "WMWHSE2",
                    "HSCode": "10255215",
                    "SKU": product.default_code,
                    "SerialCount": "0",
                    "StorerKey": "EQWEPTEST"
                }
                list_of_products.append(single_prod_data)

        data = {
            "ApplicationHeader": {
                "RequestedDate": "",
                "RequestedSystem": ""
            },
            "DataHeader": list_of_products,
            "SSA": {
                "SSA_Login": "wmeqtest",
                "SSA_Password": "WMS#2022"
            }
        }

        response_get = requests.post(url, json=data)
        response = json.loads(response_get.text)
#
#         # for product in all_products:
#         #     data = {
#         #             "ApplicationHeader": {
#         #             "RequestedDate": "",
#         #             "RequestedSystem": "",
#         #             "TransactionID": ""
#         #         },
#         #         "DataHeader": {
#         #             "Facility": "WMWHSE1",
#         #             "SKUList":[
#         #                 product.default_code
#         #             ],
#         #             "SKU_Contains": "",
#         #             "StorerKey": "Demo"
#         #         },
#         #         "SSA": {
#         #           "SSA_Login": "wmeqtest",
#         #           "SSA_Password": "WMS#2022"
#         #         }
#         #     }
#         #     response_get = requests.post(url, json=data)
#         #     response = json.loads(response_get.text)
#         #
#         #     if response and response['Lines']:
#         #         prfd = self.env['stock.quant'].create({
#         #             'location_id': 8,
#         #             'product_id': product.id,
#         #             'quantity': response['Lines'][0]['QtyOnHand']
#         #         })


class CustomPOSend(models.Model):
    _inherit = 'purchase.order'

    po_check = fields.Boolean(string='Sent Status')
    asn_check = fields.Boolean(string='ASN status')

    def sync_purchase_order(self):
        url = 'https://cportal.infor.aramex.com/WS_EDI_TEST_V02/RestService_API/InBound/ImportPO'
        all_pos = self.env['purchase.order'].search([])

        for po in all_pos:
            if not po.po_check:
                po_line = []
                for line in po.order_line:
                    single_line = {
                        "ExternLineNo": "",
                        "Notes": "",
                        "Qty": line.product_qty,
                        "RetailSKU": "",
                        "SKU": line.product_id.default_code,
                        "UnitCost": line.price_unit
                    }
                    po_line.append(single_line)
                data = {
                    "ApplicationHeader":
                        {
                            "RequestedDate": "",
                            "RequestedSystem": "TestSystem",
                            "TransactionID": "STOCKORDER-001"
                        },
                    "DataHeader":
                        {
                            "BuyerAddress":
                                {
                                    "Address1": po.partner_id.street,
                                    "Address2": po.partner_id.street2,
                                    "Address3": "",
                                    "C_ID": "",
                                    "City": po.partner_id.city,
                                    "Company": po.partner_id.company_name,
                                    "Contact": "SUPP_CONTACT",
                                    "Country": po.partner_id.country_id.code,
                                    "Email": po.partner_id.email
                                },
                            "ClinetSystemRef": po.name,
                            "Currency": po.currency_id.name,
                            "EXTERNALPOKEY2": "STOCKORDER-SUB0021",
                            "Facility": "WMWHSE2",
                            "StorerKey": "EQWEPTEST",
                            "SupplierAddress":
                                {
                                    "Company": "SUPP_COMPANY",
                                    "Contact": "SUPP_CONTACT",
                                    "Country": "DXB",
                                    "Email": "SUPP@ARAMEX.COM"
                                }
                        },
                    "DataLines": po_line,
                    "SSA":
                        {
                            "SSA_Login": "wmeqtest",
                            "SSA_Password": "WMS#2022",
                            "SSA_Token": ""
                        }
                }

                response_get = requests.post(url, json=data)
                response = json.loads(response_get.text)
                if response_get.status_code == 200:
                    po.po_check = True

    def sync_asn(self):
        url = 'https://cportal.infor.aramex.com/WS_EDI_TEST_V02/RestService_API/InBound/ImportASN'
        all_pos = self.env['purchase.order'].search([])

        for po in all_pos:
            if not po.asn_check:
                po_line = []
                external_line_no = 1
                for line in po.order_line:
                    single_line = {
                        "ExternLineNo": external_line_no,
                        "LinePO": "NOPO",
                        "Qty": line.product_qty,
                        "SKU": line.product_id.default_code,
                        "UnitCost": line.price_unit
                    }

                    po_line.append(single_line)
                    external_line_no += 1
                data = {
                    "ApplicationHeader":
                        {
                            "RequestedDate": "",
                            "RequestedSystem": "TEST",
                            "TransactionID": "UniqueID ref01"
                        },
                    "DataHeader":
                        {
                            "ClinetSystemRef": po.name,
                            "Currency": po.currency_id.name,
                            "Facility": "WMWHSE2",
                            "StorerKey": "EQWEPTEST",
                            "Notes": "Comments",
                            "Type": "Customer Return"
                        },
                    "DataLines": po_line,
                    "SSA":
                        {
                            "SSA_Login": "wmeqtest",
                            "SSA_Password": "WMS#2022",
                            "SSA_Token": ""
                        }
                }

                response_get = requests.post(url, json=data)
                response = json.loads(response_get.text)
                if response_get.status_code == 200:
                    po.asn_check = True


    # def update_asn_sku(self):
    #     url = 'https://cportal.infor.aramex.com/WS_EDI_TEST_V02/RestService_API/InBound/UpdateASN'
    #     all_pos = self.env['purchase.order'].search([])
    #
    #     # for po in all_pos:
    #     #     if po.asn_check:
    #     data = {
    #         "ASN": {
    #             "ApplicationHeader": {
    #                 "RequestedDate": "",
    #                 "RequestedSystem": "TEst",
    #                 "TransactionID": "UniqueID01"
    #             },
    #             "DataHeader": {
    #                 "BOE": "",
    #                 "ClinetSystemRef": 'P000007',
    #                 "Currency": "",
    #                 "Facility": "WMWHSE2",
    #                 "Forwarder": "",
    #                 "HSUSR1": "",
    #                 "HSUSR2": "",
    #                 "HSUSR3": "",
    #                 "HSUSR4": "",
    #                 "HSUSR5": "",
    #                 "INCOTERMS": "",
    #                 "Notes": "",
    #                 "RMA": "",
    #                 "StorerKey": "EQWEPTEST",
    #                 "Supplier": "",
    #                 "TransportationMode": "",
    #                 "Type": ""
    #             },
    #             "DataLines": {
    #                 "BOE": "",
    #                 "CDOrderKey": "",
    #                 "COO": "",
    #                 "DSUSR2": "",
    #                 "DSUSR3": "",
    #                 "DSUSR4": "",
    #                 "DSUSR5": "",
    #                 "D_RMA": "",
    #                 "ExternLineNo": "",
    #                 "HSCODE": "",
    #                 "LinePO": "",
    #                 "Lottable02": "",
    #                 "Lottable04": "",
    #                 "Lottable05": "",
    #                 "Lottable07": "",
    #                 "Lottable08": "",
    #                 "Lottable09": "",
    #                 "Lottable10": "",
    #                 "Notes": "",
    #                 "OriginalLOT": "",
    #                 "POKEY": "",
    #                 "POLINENUMBER": "",
    #                 "PurchaseOrderDocument": "",
    #                 "PurchaseOrderLine": "",
    #                 "Qty": "1",
    #                 "SKU": "TEST12",
    #                 "UnitCost": "0",
    #                 "UserDate": {
    #                     "ARX_EDI._UserDefineData": {
    #                         "Key": "",
    #                         "Value": ""
    #                     }
    #                 }
    #             },
    #             "ExtraAddresses": {
    #                 "WMSTables_Address": {
    #                     "Address1": "",
    #                     "Address2": "",
    #                     "Address3": "",
    #                     "Address4": "",
    #                     "City": "",
    #                     "Country": "",
    #                     "Email": "",
    #                     "Name1": "",
    #                     "Name2": "",
    #                     "Name3": "",
    #                     "Name4": "",
    #                     "Postal": "",
    #                     "Ref": "",
    #                     "SerialKey": "123335",
    #                     "Telephone1": "",
    #                     "Telephone2": "",
    #                     "Type": "",
    #                     "WMSRef": ""
    #                 }
    #             },
    #             "SSA": {
    #                 "SSA_Login": "wmeqtest",
    #                 "SSA_Password": "WMS#2022",
    #             }
    #         },
    #         "CreateAfterCancelling": 1
    #     }
    #     response_get = requests.post(url, json=data)
    #     response = json.loads(response_get.text)



    #
    # def pickup_creation(self):
    #
    #     {
    #         "ClientInfo": {
    #             "UserName": "{{user}}",
    #             "Password": "{{password}}",
    #             "Version": "v1.0",
    #             "AccountNumber": "{{accountno}}",
    #             "AccountPin": "{{accountpin}}",
    #             "AccountEntity": "DXB",
    #             "AccountCountryCode": "AE",
    #             "Source": 0,
    #             "PreferredLanguageCode": null
    #         },
    #         "Pickup": {
    #             "PickupAddress": {
    #                 "Line1": "Test Address",
    #                 "Line2": "Test Address Line 2",
    #                 "Line3": "",
    #                 "City": "Dubai",
    #                 "StateOrProvinceCode": "Dubai",
    #                 "PostCode": "",
    #                 "CountryCode": "AE",
    #                 "Longitude": 0,
    #                 "Latitude": 0,
    #                 "BuildingNumber": null,
    #                 "BuildingName": null,
    #                 "Floor": null,
    #                 "Apartme nt": null,
    #                 "POBox": null,
    #                 "Description": null
    #             },
    #             "PickupContact": {
    #                 "Department": "Test Department",
    #                 "PersonName": "Test Person Name",
    #                 "Title": null,
    #                 "CompanyName": "Test Person/Company Name",
    #                 "PhoneNumber1": "97148707700",
    #                 "PhoneNumber1Ext": null,
    #                 "PhoneNumber2": null,
    #                 "PhoneNumber2Ext": null,
    #                 "FaxNumber": null,
    #                 "CellPhone": "97148707700",
    #                 "EmailAddress": "pickupemail@test.com",
    #                 "Type": null
    #             },
    #             "PickupLocation": "Reception",
    #             "PickupDate": "/Date({{next_day_timestamp}})/",
    #             "ReadyTime": "/Date({{ready_time}})/",
    #             "LastPickupTime": "/Date({{last_pickup_time}})/",
    #             "ClosingTime": "/Date({{closing_time}})/",
    #             "Comments": "",
    #             "Reference1": "001",
    #             "Reference2": "",
    #             "Vehicle": "Bike",
    #             "Shipments": null,
    #             "PickupItems": [{
    #                 "ProductGroup": "DOM",
    #                 "ProductType": "ONP",
    #                 "NumberOfShipments": 1,
    #                 "PackageType": "Box",
    #                 "Payment": "P",
    #                 "ShipmentWeight": {
    #                     "Unit": "KG",
    #                     "Value": 0.5
    #                 },
    #                 "ShipmentVolume": null,
    #                 "NumberOfPieces": 1,
    #                 "CashAmount": null,
    #                 "ExtraCharges": null,
    #                 "ShipmentDimensions": {
    #                     "Length": 0,
    #                     "Width": 0,
    #                     "Height": 0,
    #                     "Unit": ""
    #                 },
    #                 "Comments": "Airway Bill Number:44097846262"
    #             }],
    #             "Status": "Ready",
    #             "ExistingShipments": null,
    #             "Branch": "",
    #             "RouteCode": ""
    #         },
    #         "Transaction": {
    #             "Reference1": "",
    #             "Reference2": "",
    #             "Reference3": "",
    #             "Reference4": "",
    #             "Reference5": ""
    #         }
    #     }
    #
    #     {
    #         "Pickup": {
    #             "PickupAddress": {
    #                 "Line1": "Test Address",
    #                 "Line2": "Test Address Line 2",
    #                 "Line3": "",
    #                 "City": "Dubai",
    #                 "StateOrProvinceCode": "Dubai",
    #                 "PostCode": "",
    #                 "CountryCode": "AE",
    #                 "Longitude": 0,
    #                 "Latitude": 0,
    #                 "BuildingNumber": null,
    #                 "BuildingName": null,
    #                 "Floor": null,
    #                 "Apartme nt": null,
    #                 "POBox": null,
    #                 "Description": null
    #             },
    #             "PickupContact": {
    #                 "Department": "Test Department",
    #                 "PersonName": "Test Person Name",
    #                 "Title": null,
    #                 "CompanyName": "Test Person/Company Name",
    #                 "PhoneNumber1": "97148707700",
    #                 "PhoneNumber1Ext": null,
    #                 "PhoneNumber2": null,
    #                 "PhoneNumber2Ext": null,
    #                 "FaxNumber": null,
    #                 "CellPhone": "97148707700",
    #                 "EmailAddress": "pickupemail@test.com",
    #                 "Type": null
    #             },
    #             "PickupLocation": "Reception",
    #             "PickupDate": "/Date({{current_timestamp}})/",
    #             "ReadyTime": "/Date(1573124400000)/",
    #             "LastPickupTime": "/Date(1573135200000)/",
    #             "ClosingTime": "/Date(1573142400000)/",
    #             "Comments": "open ended field, pass awb and item description",
    #             "Reference1": "5dff00be7ad4f30cd9c3119d",
    #             "Reference2": null,
    #             "Vehicle": null,
    #             "Shipments": null,
    #             "PickupItems": [
    #                 {
    #                     "ProductGroup": "DOM",
    #                     "ProductType": "ONP",
    #                     "NumberOfShipments": 1,
    #                     "PackageType": "item",
    #                     "Payment": "P",
    #                     "ShipmentWeight": null,
    #                     "ShipmentVolume": null,
    #                     "NumberOfPieces": 1,
    #                     "CashAmount": null,
    #                     "ExtraCharges": null,
    #                     "ShipmentDimensions": null,
    #                     "Comments": "no description"
    #                 }
    #             ],
    #             "Status": "Ready",
    #             "ExistingShipments": [
    #                 {
    #                     "Number": "44097921744",
    #                     "OriginEntity": "DXB",
    #                     "ProductGroup": "DOM"
    #                 }
    #             ],
    #             "Branch": null,
    #             "RouteCode": null,
    #             "Dispatcher": 0
    #         },
    #         "LabelInfo": null,
    #         "ClientInfo": {
    #             "UserName": "{{user}}",
    #             "Password": "{{password}}",
    #             "Version": "v1.0",
    #             "AccountNumber": "{{accountno}}",
    #             "AccountPin": "{{accountpin}}",
    #             "AccountEntity": "DXB",
    #             "AccountCountryCode": "AE",
    #             "Source": 0,
    #             "PreferredLanguageCode": null
    #         },
    #         "Transaction": null
    #     }
    #
    # def shipment_tracking(self):
    #     {
    #         "ClientInfo": {
    #             "UserName": "{{user}}",
    #             "Password": "{{password}}",
    #             "Version": "v1.0",
    #             "AccountNumber": "{{accountno}}",
    #             "AccountPin": "{{accountpin}}",
    #             "AccountEntity": "DXB",
    #             "AccountCountryCode": "AE",
    #             "Source": 0,
    #             "PreferredLanguageCode": null
    #         },
    #         "Reference": "A09E775",
    #         "Transaction": {
    #             "Reference1": "",
    #             "Reference2": "",
    #             "Reference3": "",
    #             "Reference4": "",
    #             "Reference5": ""
    #         }
    #     }

