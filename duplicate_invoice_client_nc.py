#!/usr/bin/env python3
"""
Script para detectar facturas y notas de crédito con número de comprobante duplicado en Odoo
Campo: l10n_do_fiscal_number (Localización Dominicana)

USO:
    odoo-bin shell -d nombre_base_datos < detectar_duplicados_completo.py
    
O desde la shell interactiva:
    odoo-bin shell -d nombre_base_datos
    >>> exec(open('detectar_duplicados_completo.py').read())
"""

from collections import defaultdict

# ============================================
# CONFIGURACIÓN
# ============================================

INCLUIR_FACTURAS_CLIENTE = False
INCLUIR_FACTURAS_PROVEEDOR = False
INCLUIR_NC_CLIENTE = True
INCLUIR_NC_PROVEEDOR = False
SOLO_MISMO_PARTNER = True
SOLO_MISMO_TIPO = True

# ============================================
# BUSCAR DUPLICADOS
# ============================================
def buscar_duplicados():
    """Busca documentos con l10n_do_fiscal_number duplicado"""
    
    print("\n" + "=" * 100)
    print("🔍 DETECTOR DE DUPLICADOS - ODOO (Localización Dominicana)")
    print("=" * 100)
    
    # Determinar tipos de documento a buscar
    tipos_documento = []
    tipos_descripcion = []
    
    if INCLUIR_FACTURAS_CLIENTE:
        tipos_documento.append('out_invoice')
        tipos_descripcion.append("facturas de cliente")
    
    if INCLUIR_FACTURAS_PROVEEDOR:
        tipos_documento.append('in_invoice')
        tipos_descripcion.append("facturas de proveedor")
    
    if INCLUIR_NC_CLIENTE:
        tipos_documento.append('out_refund')
        tipos_descripcion.append("notas de crédito de cliente")
    
    if INCLUIR_NC_PROVEEDOR:
        tipos_documento.append('in_refund')
        tipos_descripcion.append("notas de crédito de proveedor")
    
    if not tipos_documento:
        print("❌ Error: Debe seleccionar al menos un tipo de documento")
        return {}
    
    print(f"\n🔍 Buscando: {', '.join(tipos_descripcion)}")
    
    # Mostrar filtros activos
    filtros_activos = []
    if SOLO_MISMO_PARTNER:
        filtros_activos.append("mismo partner")
    if SOLO_MISMO_TIPO:
        filtros_activos.append("mismo tipo de documento")
    
    if filtros_activos:
        print(f"📌 Filtros: {' + '.join(filtros_activos)}")
    else:
        print(f"📌 Sin filtros: buscando duplicados entre cualquier partner y tipo")
    
    # Dominio para filtrar documentos
    domain = [
        ('move_type', 'in', tipos_documento),
        ('l10n_do_fiscal_number', '!=', False),
        ('l10n_do_fiscal_number', '!=', ''),
    ]
    
    try:
        # Buscar todos los documentos
        documentos = env['account.move'].search(domain, order='l10n_do_fiscal_number, partner_id')
        
        print(f"📊 Total de documentos encontrados: {len(documentos)}")
        
        # Agrupar según configuración
        if SOLO_MISMO_PARTNER and SOLO_MISMO_TIPO:
            # Agrupar por número fiscal + partner + tipo
            documentos_por_numero = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
            for doc in documentos:
                num = doc.l10n_do_fiscal_number
                pid = doc.partner_id.id if doc.partner_id else False
                tipo = doc.move_type
                documentos_por_numero[num][pid][tipo].append(doc)
            
            duplicados = {}
            for num, partners_dict in documentos_por_numero.items():
                for pid, tipos_dict in partners_dict.items():
                    for tipo, docs_list in tipos_dict.items():
                        if len(docs_list) > 1:
                            key = f"{num}|{pid}|{tipo}"
                            duplicados[key] = {
                                'numero_fiscal': num,
                                'partner_id': pid,
                                'move_type': tipo,
                                'documentos': docs_list
                            }
        
        elif SOLO_MISMO_PARTNER:
            # Agrupar por número fiscal + partner (cualquier tipo)
            documentos_por_numero = defaultdict(lambda: defaultdict(list))
            for doc in documentos:
                num = doc.l10n_do_fiscal_number
                pid = doc.partner_id.id if doc.partner_id else False
                documentos_por_numero[num][pid].append(doc)
            
            duplicados = {}
            for num, partners_dict in documentos_por_numero.items():
                for pid, docs_list in partners_dict.items():
                    if len(docs_list) > 1:
                        key = f"{num}|{pid}"
                        duplicados[key] = {
                            'numero_fiscal': num,
                            'partner_id': pid,
                            'move_type': None,
                            'documentos': docs_list
                        }
        
        elif SOLO_MISMO_TIPO:
            # Agrupar por número fiscal + tipo (cualquier partner)
            documentos_por_numero = defaultdict(lambda: defaultdict(list))
            for doc in documentos:
                num = doc.l10n_do_fiscal_number
                tipo = doc.move_type
                documentos_por_numero[num][tipo].append(doc)
            
            duplicados = {}
            for num, tipos_dict in documentos_por_numero.items():
                for tipo, docs_list in tipos_dict.items():
                    if len(docs_list) > 1:
                        key = f"{num}|{tipo}"
                        duplicados[key] = {
                            'numero_fiscal': num,
                            'partner_id': None,
                            'move_type': tipo,
                            'documentos': docs_list
                        }
        
        else:
            # Agrupar solo por número fiscal (cualquier partner y tipo)
            documentos_por_numero = defaultdict(list)
            for doc in documentos:
                documentos_por_numero[doc.l10n_do_fiscal_number].append(doc)
            
            duplicados = {
                num: {
                    'numero_fiscal': num,
                    'partner_id': None,
                    'move_type': None,
                    'documentos': docs_list
                }
                for num, docs_list in documentos_por_numero.items() 
                if len(docs_list) > 1
            }
        
        return duplicados
    
    except Exception as e:
        print(f"❌ Error al buscar documentos: {e}")
        import traceback
        traceback.print_exc()
        return {}


# ============================================
# MAPEO DE TIPOS
# ============================================
TIPOS_DOCUMENTO = {
    'out_invoice': 'Factura Cliente',
    'in_invoice': 'Factura Proveedor',
    'out_refund': 'NC Cliente',
    'in_refund': 'NC Proveedor',
}


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
        documentos = data['documentos']
        partner_id = data['partner_id']
        move_type = data['move_type']
        
        # Header del grupo
        header = f"\n🔴 Número Fiscal: {numero_fiscal}"
        
        if partner_id and SOLO_MISMO_PARTNER:
            partner_name = documentos[0].partner_id.name if documentos[0].partner_id else 'Sin nombre'
            header += f" | Partner: {partner_name} (ID: {partner_id})"
        
        if move_type and SOLO_MISMO_TIPO:
            header += f" | Tipo: {TIPOS_DOCUMENTO.get(move_type, move_type)}"
        
        print(header)
        print(f"   Cantidad de documentos: {len(documentos)}")
        
        # Análisis de variaciones
        partners_unicos = set(d.partner_id.id if d.partner_id else False for d in documentos)
        tipos_unicos = set(d.move_type for d in documentos)
        
        alertas = []
        if len(partners_unicos) > 1:
            alertas.append(f"{len(partners_unicos)} partners diferentes")
        if len(tipos_unicos) > 1:
            tipos_nombres = [TIPOS_DOCUMENTO.get(t, t) for t in tipos_unicos]
            alertas.append(f"tipos mezclados ({', '.join(tipos_nombres)})")
        
        if alertas:
            print(f"   ⚠️  ALERTA: {' + '.join(alertas)}!")
        
        print("-" * 100)
        
        # Listar documentos
        for i, doc in enumerate(documentos, 1):
            partner_name = doc.partner_id.name if doc.partner_id else 'Sin partner'
            tipo_doc = TIPOS_DOCUMENTO.get(doc.move_type, doc.move_type)
            
            # Obtener estado en español
            try:
                estado = dict(doc._fields['state'].selection).get(doc.state, doc.state)
            except:
                estado = doc.state
            
            fecha = doc.invoice_date or 'Sin fecha'
            monto = doc.amount_total
            
            print(f"   {i}. ID: {doc.id:<8} | "
                  f"Tipo: {tipo_doc:<18} | "
                  f"Documento: {doc.name:<20} | "
                  f"Partner: {partner_name:<30} | "
                  f"Fecha: {fecha} | "
                  f"Monto: ${monto:,.2f} | "
                  f"Estado: {estado}")
        
        print("-" * 100)
    
    # Resumen general
    total_documentos = sum(len(data['documentos']) for data in duplicados.values())
    print(f"\n📊 RESUMEN GENERAL:")
    print(f"   • Grupos de números fiscales duplicados: {len(duplicados)}")
    print(f"   • Total de documentos afectados: {total_documentos}")
    
    # Análisis por tipo de documento
    contador_tipos = defaultdict(int)
    for data in duplicados.values():
        for doc in data['documentos']:
            contador_tipos[doc.move_type] += 1
    
    if contador_tipos:
        print(f"\n📋 DOCUMENTOS AFECTADOS POR TIPO:")
        for tipo, cantidad in sorted(contador_tipos.items()):
            nombre_tipo = TIPOS_DOCUMENTO.get(tipo, tipo)
            print(f"   • {nombre_tipo}: {cantidad}")
    
    # Análisis crítico
    if not SOLO_MISMO_PARTNER or not SOLO_MISMO_TIPO:
        grupos_mismo_partner = sum(1 for data in duplicados.values() 
                                   if len(set(d.partner_id.id if d.partner_id else False 
                                            for d in data['documentos'])) == 1)
        
        grupos_mismo_tipo = sum(1 for data in duplicados.values()
                               if len(set(d.move_type for d in data['documentos'])) == 1)
        
        print(f"\n⚠️  ANÁLISIS CRÍTICO:")
        
        if not SOLO_MISMO_PARTNER:
            grupos_dif_partners = len(duplicados) - grupos_mismo_partner
            print(f"   • Duplicados del mismo partner: {grupos_mismo_partner}")
            print(f"   • Duplicados entre diferentes partners: {grupos_dif_partners}", end="")
            if grupos_dif_partners > 0:
                print(" (¡REVISAR URGENTE!)")
            else:
                print()
        
        if not SOLO_MISMO_TIPO:
            grupos_dif_tipos = len(duplicados) - grupos_mismo_tipo
            print(f"   • Mismo tipo de documento: {grupos_mismo_tipo}")
            print(f"   • Tipos mezclados (Factura + NC, etc.): {grupos_dif_tipos}", end="")
            if grupos_dif_tipos > 0:
                print(" (¡VERIFICAR!)")
            else:
                print()


# ============================================
# EXPORTAR A CSV
# ============================================
def exportar_a_csv(duplicados, filename='duplicados_completo.csv'):
    """Exporta los resultados a un archivo CSV"""
    import csv
    
    if not duplicados:
        print("No hay duplicados para exportar.")
        return
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['numero_fiscal', 'id_documento', 'tipo_documento', 'tipo_nombre',
                         'nombre_documento', 'partner_id', 'partner_nombre', 'fecha', 
                         'monto', 'estado', 'moneda']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for key, data in sorted(duplicados.items(), key=lambda x: x[1]['numero_fiscal']):
                numero_fiscal = data['numero_fiscal']
                documentos = data['documentos']
                
                for doc in documentos:
                    writer.writerow({
                        'numero_fiscal': numero_fiscal,
                        'id_documento': doc.id,
                        'tipo_documento': doc.move_type,
                        'tipo_nombre': TIPOS_DOCUMENTO.get(doc.move_type, doc.move_type),
                        'nombre_documento': doc.name,
                        'partner_id': doc.partner_id.id if doc.partner_id else '',
                        'partner_nombre': doc.partner_id.name if doc.partner_id else '',
                        'fecha': doc.invoice_date or '',
                        'monto': doc.amount_total,
                        'estado': doc.state,
                        'moneda': doc.currency_id.name or ''
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
    duplicados = buscar_duplicados()
    
    # Mostrar resultados
    mostrar_duplicados(duplicados)
    
    # Preguntar si desea exportar
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