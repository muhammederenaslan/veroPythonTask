import argparse
import requests
import pandas as pd
from datetime import datetime, timedelta

def send_csv_to_server(csv_filename, keys, colored=True):
    url = "http://localhost:5000/process_csv"  
    data = open(csv_filename, 'rb').read()
    headers = {
        'Content-Type': 'application/csv'
    }

    keys_param = ','.join(keys)
    
    params = {'keys': keys_param}

    params['colored'] = str(colored).lower()

    response = requests.post(url, data=data, headers=headers, params=params)
    if response.status_code == 200:
        response_data = response.json()

        df = pd.DataFrame(response_data)

        df['hu'] = df['hu'].replace('null', None)

        df = df.sort_values(by=['gruppe'])

        if 'color' in df.columns:
            df = df.drop(columns=['color'])

        current_date = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        excel_filename = f'vehicles_{current_date}.xlsx'

        writer = pd.ExcelWriter(excel_filename, engine='xlsxwriter')

        df.to_excel(writer, sheet_name='Sheet1', index=False)

        workbook = writer.book
        worksheet = writer.sheets['Sheet1']

        if colored:
            green_format = workbook.add_format({'bg_color': '#007500'})
            orange_format = workbook.add_format({'bg_color': '#FFA500'})
            red_format = workbook.add_format({'bg_color': '#b30000'})

            for row_num, hu in enumerate(df['hu'], start=1):
                if hu is not None:
                    hu_date = datetime.strptime(hu, '%Y-%m-%d')
                    three_months_ago = datetime.now() - timedelta(days=90)
                    twelve_months_ago = datetime.now() - timedelta(days=365)

                    if hu_date >= three_months_ago:
                        worksheet.set_row(row_num, None, green_format)
                    elif hu_date >= twelve_months_ago:
                        worksheet.set_row(row_num, None, orange_format)
                    else:
                        worksheet.set_row(row_num, None, red_format)

        writer._save()

        print(f'Excel file "{excel_filename}" has been created.')
    else:
        print(f'Error: {response.status_code} - {response.text}')        

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client for sending CSV data to the server and generating an Excel file.")
    parser.add_argument("csv_file", help="CSV file containing vehicle information")
    parser.add_argument("-k", "--keys", nargs='+', help="Additional keys to include in Excel")
    parser.add_argument("-c", "--colored", action="store_true", help="Color rows in Excel based on hu")

    args = parser.parse_args()

    if not args.keys:
        args.keys = []

    if args.colored:
        print("Colored is set to True.")
    else:
        print("Colored is set to False.")

    send_csv_to_server(args.csv_file, args.keys, args.colored)
