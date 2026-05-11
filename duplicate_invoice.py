#!/usr/bin/env python3
"""
Script para detectar facturas con número de comprobante duplicado en Odoo
Campo: l10n_do_fiscal_number (Localización Dominicana)

USO:
    odoo-bin shell -d nombre_base_datos < detectar_facturas_duplicadas_shell.py
    
O desde la shell interactiva:
    odoo-bin shell -d nombre_base_datos
    >>> exec(open('detectar_facturas_duplicadas_shell.py').read())
"""

from collections import defaultdict

# ============================================
# CONFIGURACIÓN
# ============================================
INCLUIR_FACTURAS_CLIENTE = True      # Facturas de cliente (out_invoice)
INCLUIR_FACTURAS_PROVEEDOR = False   # Facturas de proveedor (in_invoice)
SOLO_MISMO_PARTNER = False            # Solo mostrar duplicados del mismo partner

# ============================================
# BUSCAR FACTURAS DUPLICADAS
# ============================================
def buscar_facturas_duplicadas():
    """Busca facturas con l10n_do_fiscal_number duplicado"""
    
    print("\n" + "=" * 100)
    print("🔍 DETECTOR DE FACTURAS DUPLICADAS - ODOO (Localización Dominicana)")
    print("=" * 100)
    
    # Determinar tipos de factura a buscar
    tipos_factura = []
    if INCLUIR_FACTURAS_CLIENTE:
        tipos_factura.append('out_invoice')
    if INCLUIR_FACTURAS_PROVEEDOR:
        tipos_factura.append('in_invoice')
    
    if not tipos_factura:
        print("❌ Error: Debe seleccionar al menos un tipo de factura")
        return {}
    
    tipo_texto = []
    if INCLUIR_FACTURAS_CLIENTE:
        tipo_texto.append("clientes")
    if INCLUIR_FACTURAS_PROVEEDOR:
        tipo_texto.append("proveedores")
    
    print(f"\n🔍 Buscando facturas de {' y '.join(tipo_texto)}...")
    if SOLO_MISMO_PARTNER:
        print("📌 Filtro: Solo duplicados del mismo partner")
    else:
        print("📌 Filtro: Duplicados entre cualquier partner")
    
    # Dominio para filtrar facturas con número fiscal no vacío
    domain = [
        ('move_type', 'in', tipos_factura),      # Tipos seleccionados
        ('l10n_do_fiscal_number', '!=', False),  # Con número fiscal
        ('l10n_do_fiscal_number', '!=', ''),     # No vacío
    ]
    
    try:
        # Buscar todas las facturas que cumplan el criterio
        facturas = env['account.move'].search(domain, order='l10n_do_fiscal_number, partner_id')
        
        print(f"📊 Total de facturas encontradas: {len(facturas)}")
        
        # Agrupar facturas por número fiscal
        if SOLO_MISMO_PARTNER:
            # Agrupar por número fiscal Y partner
            facturas_por_numero = defaultdict(lambda: defaultdict(list))
            for factura in facturas:
                numero_fiscal = factura.l10n_do_fiscal_number
                partner_id = factura.partner_id.id if factura.partner_id else False
                facturas_por_numero[numero_fiscal][partner_id].append(factura)
            
            # Encontrar duplicados (mismo número fiscal y mismo partner)
            duplicados = {}
            for numero_fiscal, partners_dict in facturas_por_numero.items():
                for partner_id, facturas_list in partners_dict.items():
                    if len(facturas_list) > 1:
                        key = f"{numero_fiscal}|{partner_id}"
                        duplicados[key] = {
                            'numero_fiscal': numero_fiscal,
                            'partner_id': partner_id,
                            'facturas': facturas_list
                        }
        else:
            # Agrupar solo por número fiscal (cualquier partner)
            facturas_por_numero = defaultdict(list)
            for factura in facturas:
                numero_fiscal = factura.l10n_do_fiscal_number
                facturas_por_numero[numero_fiscal].append(factura)
            
            # Encontrar duplicados
            duplicados = {
                numero: {
                    'numero_fiscal': numero,
                    'partner_id': None,
                    'facturas': facturas_list
                }
                for numero, facturas_list in facturas_por_numero.items() 
                if len(facturas_list) > 1
            }
        
        return duplicados
    
    except Exception as e:
        print(f"❌ Error al buscar facturas: {e}")
        import traceback
        traceback.print_exc()
        return {}


# ============================================
# MOSTRAR RESULTADOS
# ============================================
def mostrar_duplicados(duplicados):
    """Muestra los duplicados encontrados de forma organizada"""
    
    if not duplicados:
        print("\n✅ ¡Excelente! No se encontraron números fiscales duplicados.")
        return
    
    print(f"\n⚠️  SE ENCONTRARON {len(duplicados)} GRUPOS DE NÚMEROS FISCALES DUPLICADOS\n")
    print("=" * 100)
    
    for key, data in sorted(duplicados.items(), key=lambda x: x[1]['numero_fiscal']):
        numero_fiscal = data['numero_fiscal']
        facturas = data['facturas']
        partner_id = data['partner_id']
        
        # Obtener nombre del partner si aplica
        if partner_id and SOLO_MISMO_PARTNER:
            partner_name = facturas[0].partner_id.name if facturas[0].partner_id else 'Sin nombre'
            print(f"\n🔴 Número Fiscal: {numero_fiscal} | Partner: {partner_name} (ID: {partner_id})")
        else:
            print(f"\n🔴 Número Fiscal Duplicado: {numero_fiscal}")
        
        print(f"   Cantidad de facturas: {len(facturas)}")
        
        # Verificar si hay diferentes partners en este grupo
        partners_unicos = set(f.partner_id.id if f.partner_id else False for f in facturas)
        if len(partners_unicos) > 1:
            print(f"   ⚠️  ALERTA: Múltiples partners ({len(partners_unicos)}) usando el mismo número fiscal!")
        
        print("-" * 100)
        
        for i, factura in enumerate(facturas, 1):
            partner_name = factura.partner_id.name or 'Sin cliente'
            tipo_factura = dict(factura._fields['move_type'].selection).get(factura.move_type, factura.move_type)
            estado = dict(factura._fields['state'].selection).get(factura.state, factura.state)
            fecha = factura.invoice_date or 'Sin fecha'
            monto = factura.amount_total
            
            print(f"   {i}. ID: {factura.id:<8} | "
                  f"Tipo: {tipo_factura:<20} | "
                  f"Factura: {factura.name:<20} | "
                  f"Partner: {partner_name:<30} | "
                  f"Fecha: {fecha} | "
                  f"Monto: ${monto:,.2f} | "
                  f"Estado: {estado}")
        
        print("-" * 100)
    
    # Resumen
    total_facturas_duplicadas = sum(len(data['facturas']) for data in duplicados.values())
    print(f"\n📊 RESUMEN:")
    print(f"   • Grupos de números fiscales duplicados: {len(duplicados)}")
    print(f"   • Total de facturas afectadas: {total_facturas_duplicadas}")
    
    # Análisis adicional
    grupos_mismo_partner = sum(1 for data in duplicados.values() 
                               if len(set(f.partner_id.id if f.partner_id else False 
                                        for f in data['facturas'])) == 1)
    grupos_diferentes_partners = len(duplicados) - grupos_mismo_partner
    
    if not SOLO_MISMO_PARTNER and grupos_diferentes_partners > 0:
        print(f"\n⚠️  ANÁLISIS CRÍTICO:")
        print(f"   • Duplicados del mismo partner: {grupos_mismo_partner}")
        print(f"   • Duplicados entre diferentes partners: {grupos_diferentes_partners} (¡REVISAR URGENTE!)")



# ============================================
# EXPORTAR A CSV (OPCIONAL)
# ============================================
def exportar_a_csv(duplicados, filename='facturas_duplicadas.csv'):
    """Exporta los resultados a un archivo CSV"""
    import csv
    
    if not duplicados:
        print("No hay duplicados para exportar.")
        return
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['numero_fiscal', 'id_factura', 'tipo_factura', 'nombre_factura', 
                         'partner_id', 'partner_nombre', 'fecha', 'monto', 'estado', 'moneda']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for key, data in sorted(duplicados.items(), key=lambda x: x[1]['numero_fiscal']):
                numero_fiscal = data['numero_fiscal']
                facturas = data['facturas']
                
                for factura in facturas:
                    writer.writerow({
                        'numero_fiscal': numero_fiscal,
                        'id_factura': factura.id,
                        'tipo_factura': factura.move_type,
                        'nombre_factura': factura.name,
                        'partner_id': factura.partner_id.id if factura.partner_id else '',
                        'partner_nombre': factura.partner_id.name if factura.partner_id else '',
                        'fecha': factura.invoice_date or '',
                        'monto': factura.amount_total,
                        'estado': factura.state,
                        'moneda': factura.currency_id.name or ''
                    })
        
        print(f"\n💾 Resultados exportados a: {filename}")
    
    except Exception as e:
        print(f"❌ Error al exportar a CSV: {e}")


# ============================================
# FUNCIÓN PRINCIPAL
# ============================================
def main():
    """Función principal del script"""
    
    # Buscar duplicados
    duplicados = buscar_facturas_duplicadas()
    
    # Mostrar resultados
    mostrar_duplicados(duplicados)
    
    # Preguntar si desea exportar (comentar si se ejecuta en modo no interactivo)
    if duplicados:
        print("\n" + "=" * 100)
        respuesta = input("¿Deseas exportar los resultados a CSV? (s/n): ").lower()
        if respuesta == 's':
            exportar_a_csv(duplicados)
    
    print("\n" + "=" * 100)
    print("✅ Proceso completado")
    print("=" * 100)


# ============================================
# EJECUTAR
# ============================================
if __name__ == "__main__":
    main()