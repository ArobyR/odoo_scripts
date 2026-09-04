#!/usr/bin/env python3
"""
Script para detectar facturas de proveedor (pagos al exterior) con NÚMERO DE COMPROBANTE FISCAL duplicado.
Clasifica los resultados en:
  1. Duplicados del MISMO proveedor.
  2. Duplicados de DIFERENTE proveedor.

USO:
    odoo-bin shell -d nombre_base_datos < duplicate_foreign_invoices.py

O desde la shell interactiva:
    odoo-bin shell -d nombre_base_datos
    >>> exec(open('duplicate_foreign_invoices.py').read())
"""

from collections import defaultdict
import csv

# ============================================================
# CONFIGURACIÓN — ajusta según lo que necesites detectar
# ============================================================

# Filtrar solo por las compañías accesibles en la sesión actual.
# True  → env.companies (las que tiene el usuario activo)
# False → todas las compañías de la base de datos
FILTRAR_POR_COMPANIAS_ACTIVAS = False

# ============================================================
# BUSCAR DUPLICADOS
# ============================================================
def buscar_duplicados():
    print("\n" + "=" * 110)
    print("🔍 DETECTOR DE DUPLICADOS - PAGOS AL EXTERIOR (Por Comprobante Fiscal)")
    print("=" * 110)

    # Dominio base
    domain = [
        ('move_type', '=', 'in_invoice'),  # Facturas de proveedor
        ('l10n_do_fiscal_number', '!=', False), # Que tengan NCF
        ('l10n_do_fiscal_number', '!=', ''),
    ]

    # Identificación de Pagos al Exterior
    # NOTA: En la localización dominicana, los pagos al exterior suelen llevar NCF B17 o E34.
    domain.append('|')
    domain.append(('l10n_do_fiscal_number', '=ilike', 'B17%'))
    domain.append(('l10n_do_fiscal_number', '=ilike', 'E34%'))

    # Filtro por compañías activas (opcional)
    if FILTRAR_POR_COMPANIAS_ACTIVAS:
        companias_ids = env.companies.ids
        domain.append(('company_id', 'in', companias_ids))
        nombres = ', '.join(env.companies.mapped('name'))
        print(f"🏢 Empresas        : {nombres}")
    else:
        print("🏢 Empresas        : todas las de la base de datos")

    try:
        documentos = env['account.move'].sudo().search(
            domain,
            order='company_id, l10n_do_fiscal_number, partner_id'
        )
        print(f"\n📊 Total de documentos de pago al exterior encontrados: {len(documentos)}")

        # Agrupar por NCF y Empresa (Para evitar mezclar de distintas empresas)
        grupos = defaultdict(list)
        for doc in documentos:
            ncf_limpio = str(doc.l10n_do_fiscal_number).strip().upper() if doc.l10n_do_fiscal_number else ''
            key = f"{doc.company_id.id if doc.company_id else 'none'}|{ncf_limpio}"
            grupos[key].append(doc)

        duplicados_mismo_prov = {}
        duplicados_dif_prov = {}

        for key, docs in grupos.items():
            if len(docs) > 1:
                # Determinar si son del mismo proveedor o diferentes
                partners_unicos = set(d.partner_id.id for d in docs if d.partner_id)
                
                ncf_limpio = str(docs[0].l10n_do_fiscal_number).strip().upper()

                info = {
                    'numero_fiscal': ncf_limpio,
                    'company_id': docs[0].company_id.id if docs[0].company_id else None,
                    'company_name': docs[0].company_id.name if docs[0].company_id else 'Sin empresa',
                    'documentos': docs,
                    'partners_unicos': len(partners_unicos)
                }

                if len(partners_unicos) == 1:
                    duplicados_mismo_prov[key] = info
                else:
                    duplicados_dif_prov[key] = info

        return duplicados_mismo_prov, duplicados_dif_prov

    except Exception as e:
        print(f"❌ Error al buscar documentos: {e}")
        import traceback
        traceback.print_exc()
        return {}, {}


# ============================================================
# MOSTRAR RESULTADOS
# ============================================================
def mostrar_grupo_duplicados(titulo, duplicados, alerta=False):
    if not duplicados:
        print(f"\n✅ No se encontraron {titulo.lower()}.")
        return

    simbolo = "🔴" if alerta else "🟡"
    print(f"\n{simbolo} SE ENCONTRARON {len(duplicados)} GRUPOS DE: {titulo.upper()}\n")
    print("=" * 110)

    for key, data in sorted(duplicados.items(), key=lambda x: (
        x[1].get('company_name', ''),
        x[1]['numero_fiscal']
    )):
        numero_fiscal = data['numero_fiscal']
        documentos = data['documentos']

        # Encabezado del grupo
        header = f"\n{simbolo} NCF Duplicado: {numero_fiscal}"
        if data.get('company_name'):
            header += f"  |  Empresa: {data['company_name']}"

        if data['partners_unicos'] == 1:
            partner_name = documentos[0].partner_id.name or 'Sin nombre'
            header += f"  |  Proveedor: {partner_name}"
        else:
            header += f"  |  ⚠️ MÚLTIPLES PROVEEDORES ({data['partners_unicos']})"

        print(header)
        print(f"   Total facturas en este grupo: {len(documentos)}")
        print("-" * 110)

        for i, doc in enumerate(documentos, 1):
            empresa      = doc.company_id.name if doc.company_id else 'Sin empresa'
            partner_name = doc.partner_id.name if doc.partner_id else 'Sin partner'
            
            try:
                estado = dict(doc._fields['state'].selection).get(doc.state, doc.state)
            except Exception:
                estado = doc.state

            fecha = doc.invoice_date or 'Sin fecha'
            referencia = doc.ref or 'Sin ref'

            print(f"   {i}. ID: {doc.id:<8} | "
                  f"Ref: {referencia:<15} | "
                  f"Empresa: {empresa:<20} | "
                  f"Proveedor: {partner_name:<25} | "
                  f"Fecha: {fecha} | "
                  f"Monto: ${doc.amount_total:>12,.2f} | "
                  f"Estado: {estado}")

        print("-" * 110)


# ============================================================
# EXPORTAR A CSV
# ============================================================
def exportar_a_csv(mismo_prov, dif_prov, filename='duplicados_pago_exterior.csv'):
    if not mismo_prov and not dif_prov:
        print("No hay duplicados para exportar.")
        return

    fieldnames = [
        'clasificacion', 'numero_fiscal', 'company_id', 'company_nombre',
        'id_documento', 'referencia', 'partner_id', 'partner_nombre', 'fecha', 'monto', 'estado', 'moneda'
    ]

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Función helper para escribir
            def escribir_grupo(duplicados, clasificacion_texto):
                for key, data in sorted(duplicados.items(), key=lambda x: (
                    x[1].get('company_name', ''), x[1]['numero_fiscal']
                )):
                    for doc in data['documentos']:
                        try:
                            estado = dict(doc._fields['state'].selection).get(doc.state, doc.state)
                        except Exception:
                            estado = doc.state

                        writer.writerow({
                            'clasificacion'   : clasificacion_texto,
                            'numero_fiscal'   : data['numero_fiscal'],
                            'company_id'      : doc.company_id.id if doc.company_id else '',
                            'company_nombre'  : doc.company_id.name if doc.company_id else '',
                            'id_documento'    : doc.id,
                            'referencia'      : doc.ref or '',
                            'partner_id'      : doc.partner_id.id if doc.partner_id else '',
                            'partner_nombre'  : doc.partner_id.name if doc.partner_id else '',
                            'fecha'           : doc.invoice_date or '',
                            'monto'           : doc.amount_total,
                            'estado'          : estado,
                            'moneda'          : doc.currency_id.name if doc.currency_id else '',
                        })

            escribir_grupo(mismo_prov, 'MISMO PROVEEDOR')
            escribir_grupo(dif_prov, 'DIFERENTE PROVEEDOR')

        print(f"\n💾 Resultados exportados a: {filename}")

    except Exception as e:
        print(f"❌ Error al exportar a CSV: {e}")


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================
def main():
    mismo_prov, dif_prov = buscar_duplicados()
    
    # Mostrar primero los de diferentes proveedores (suelen ser errores críticos)
    mostrar_grupo_duplicados("Duplicados con DIFERENTE Proveedor", dif_prov, alerta=True)
    mostrar_grupo_duplicados("Duplicados con el MISMO Proveedor", mismo_prov, alerta=False)

    total_grupos = len(mismo_prov) + len(dif_prov)
    
    print(f"\n📊 RESUMEN GENERAL:")
    print(f"   • Grupos duplicados (Mismo Proveedor): {len(mismo_prov)}")
    print(f"   • Grupos duplicados (Dif. Proveedor) : {len(dif_prov)}")
    print(f"   • Total de NCFs duplicados           : {total_grupos}")

    if total_grupos > 0:
        print("\n" + "=" * 110)
        respuesta = input("¿Deseas exportar los resultados a CSV? (s/n): ").lower()
        if respuesta == 's':
            exportar_a_csv(mismo_prov, dif_prov)

    print("\n" + "=" * 110)
    print("✅ Proceso completado")
    print("=" * 110)


if __name__ == "__main__":
    main()
