from flask import Flask, request, jsonify
import requests
import csv
import json
from datetime import datetime, timedelta

app = Flask(__name__)

def get_access_token():
    auth_url = "https://api.baubuddy.de/index.php/login"
    headers = {
        "Authorization": "Basic QVBJX0V4cGxvcmVyOjEyMzQ1NmlzQUxhbWVQYXNz",
        "Content-Type": "application/json"
    }
    data = {
        "username": "365",
        "password": "1"
    }

    response = requests.post(auth_url, headers=headers, json=data)
    access_token = response.json()["oauth"]["access_token"]
    return access_token

def resolve_color(labelIds):
    color_url = "https://api.baubuddy.de/dev/index.php/v1/labels/"
    headers = {
        "Authorization": f"Bearer {get_access_token()}"
    }
    colors = {}

    for labelId in labelIds:
        response = requests.get(f"{color_url}{labelId}", headers=headers)
        if response.status_code == 200:
            label_data = response.json()
            colors[labelId] = label_data.get("colorCode", None)

    return colors

def color_row(hu, colored):
    if hu == 'null':
        return {'color': 'white', 'value': None}  
    elif hu is None and colored:
        return {'color': 'white', 'value': 'null'}  
    else:
        try:
            hu_date = datetime.strptime(hu, '%Y-%m-%d')
            three_months_ago = datetime.now() - timedelta(days=90)
            twelve_months_ago = datetime.now() - timedelta(days=365)

            if hu_date >= three_months_ago:
                return {'color': 'green', 'value': hu}
            elif hu_date >= twelve_months_ago:
                return {'color': 'orange', 'value': hu}
            else:
                return {'color': 'red', 'value': hu}
        except ValueError:
            return {'color': 'white', 'value': 'invalid_date'}  

@app.route('/process_csv', methods=['POST'])
def process_csv():
    try:
        data = request.data.decode('utf-8')
        csv_data = csv.reader(data.splitlines(), delimiter=';')  
        header = next(csv_data, None) 

        if header is None:
            return jsonify({"error": "CSV file is empty"}), 400

        kurzname_index = None
        for i, column in enumerate(header):
            if column.strip().lower() == "kurzname":  
                kurzname_index = i
                break

        if kurzname_index is None:
            return jsonify({"error": "CSV file does not contain a 'kurzname' column"}), 400

        kurznames = []  
        for row in csv_data:
            if len(row) > kurzname_index:  
                kurzname = row[kurzname_index]
                kurznames.append(kurzname)

        resources_url = "https://api.baubuddy.de/dev/index.php/v1/vehicles/select/active"
        headers = {
            "Authorization": f"Bearer {get_access_token()}"
        }

        response = requests.get(resources_url, headers=headers)
        resources = response.json()

        client_keys_param = request.args.get('keys', '')  
        client_keys = client_keys_param.split(',') 
        print(client_keys)
        colored = request.args.get('colored')
        print(colored)


        if colored == 'true':
            colored_rows = [color_row(resource.get("hu"), colored == 'true') for resource in resources]
        elif colored == 'false':
            colored_rows = [color_row(resource.get("hu"), colored == 'false') for resource in resources]


        matched_data = []
        for resource, colored_row in zip(resources, colored_rows):
            if resource.get("kurzname") in kurznames:
                data_entry = {"rnr": resource["rnr"], "gruppe": resource.get("gruppe")}

                for key in client_keys:
                    if key in resource:
                        data_entry[key] = resource[key]

                data_entry["gruppe"] = resource.get("gruppe", "Unknown")
                
                
                data_entry['color'] = 'green'  


                data_entry["hu"] = colored_row['value']  

                if 'labelIds' in client_keys:
                    data_entry['labelIds'] = resource.get("labelIds", "Unknown")

                matched_data.append(data_entry)

        filtered_data = [d for d in matched_data if d.get("rnr")]

        filtered_data.sort(key=lambda x: x.get("rnr", ""))
        print(filtered_data)
        return jsonify(filtered_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
