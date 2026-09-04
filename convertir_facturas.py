import pandas as pd
import re
import sys

def parse_and_convert(input_path, output_path='output.csv'):
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    data = []
    for line in lines:
        # Nuevo patrón con Comprobante
        match = re.search(r'ID:\s*(\d+)\s*\|\s*Comprobante:\s*(.*?)\s*\|\s*Empresa:\s*(.*?)\s*\|\s*Tipo:\s*(.*?)\s*\|\s*Documento:\s*(.*?)\s*\|\s*Partner:\s*(.*?)\s*\|\s*Fecha:\s*(.*?)\s*\|\s*Monto:\s*\$?\s*([\d,]+(?:\.\d+)?)\s*\|\s*Estado:\s*(.*)', line)
        if match:
            id_, comprobante, empresa, tipo, documento, partner, fecha, monto_str, estado = match.groups()
            monto = monto_str.replace(',', '').strip()
            data.append([id_, comprobante, empresa, tipo, documento, partner, fecha, monto, estado])
    df = pd.DataFrame(data, columns=['ID', 'Comprobante', 'Empresa', 'Tipo', 'Documento', 'Partner', 'Fecha', 'Monto', 'Estado'])
    df = df.astype(str)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f'Archivo CSV generado: {output_path}')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Uso: python script.py ruta_del_archivo.txt [output.csv]')
    else:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'output.csv'
        parse_and_convert(input_file, output_file)