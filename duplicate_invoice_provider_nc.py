#!/usr/bin/env python3
"""
Script para detectar documentos contables con número de comprobante duplicado en Odoo
Campo: l10n_do_fiscal_number (Localización Dominicana)

Soporta entornos multicompañía — los duplicados se evalúan DENTRO de la misma empresa
para evitar falsos positivos cuando distintas compañías comparten base de datos.

USO:
    odoo-bin shell -d nombre_base_datos < duplicate_invoice_unified.py

O desde la shell interactiva:
    odoo-bin shell -d nombre_base_datos
    >>> exec(open('duplicate_invoice_unified.py').read())
"""

from collections import defaultdict

# ============================================================
# CONFIGURACIÓN — ajusta según lo que necesites detectar
# ============================================================

# Tipos de documento a incluir en la búsqueda
INCLUIR_FACTURAS_CLIENTE  = False    # out_invoice
INCLUIR_FACTURAS_PROVEEDOR = False   # in_invoice
INCLUIR_NC_CLIENTE        = False    # out_refund
INCLUIR_NC_PROVEEDOR      = True    # in_refund

# Dimensiones de agrupación para determinar si es duplicado
SOLO_MISMA_EMPRESA = True   # Agrupar por company_id  (recomendado en multicompañía)
SOLO_MISMO_PARTNER = False   # Agrupar por partner_id
SOLO_MISMO_TIPO    = True   # Agrupar por move_type

# Filtrar solo por las compañías accesibles en la sesión actual.
# True  → env.companies (las que tiene el usuario activo)
# False → todas las compañías de la base de datos
FILTRAR_POR_COMPANIAS_ACTIVAS = False

# ============================================================
# MAPEO DE TIPOS
# ============================================================
TIPOS_DOCUMENTO = {
    'out_invoice': 'Factura Cliente',
    'in_invoice' : 'Factura Proveedor',
    'out_refund' : 'NC Cliente',
    'in_refund'  : 'NC Proveedor',
}


# ============================================================
# BUSCAR DUPLICADOS
# ============================================================
def buscar_duplicados():
    """Busca documentos con l10n_do_fiscal_number duplicado."""

    print("\n" + "=" * 110)
    print("🔍 DETECTOR DE DUPLICADOS - ODOO (Localización Dominicana)")
    print("=" * 110)

    # Determinar tipos de documento
    tipos_documento = []
    tipos_descripcion = []

    if INCLUIR_FACTURAS_CLIENTE:
        tipos_documento.append('out_invoice')
        tipos_descripcion.append("Facturas Cliente")
    if INCLUIR_FACTURAS_PROVEEDOR:
        tipos_documento.append('in_invoice')
        tipos_descripcion.append("Facturas Proveedor")
    if INCLUIR_NC_CLIENTE:
        tipos_documento.append('out_refund')
        tipos_descripcion.append("NC Cliente")
    if INCLUIR_NC_PROVEEDOR:
        tipos_documento.append('in_refund')
        tipos_descripcion.append("NC Proveedor")

    if not tipos_documento:
        print("❌ Error: Debe seleccionar al menos un tipo de documento.")
        return {}

    print(f"\n📄 Tipos incluidos : {', '.join(tipos_descripcion)}")

    # Mostrar dimensiones de agrupación activas
    dimensiones = []
    if SOLO_MISMA_EMPRESA:
        dimensiones.append("misma empresa")
    if SOLO_MISMO_PARTNER:
        dimensiones.append("mismo partner")
    if SOLO_MISMO_TIPO:
        dimensiones.append("mismo tipo de documento")

    if dimensiones:
        print(f"📌 Agrupar por     : número fiscal + {' + '.join(dimensiones)}")
    else:
        print("📌 Agrupar por     : número fiscal únicamente (sin filtros adicionales)")

    # Dominio base
    domain = [
        ('move_type', 'in', tipos_documento),
        ('l10n_do_fiscal_number', '!=', False),
        ('l10n_do_fiscal_number', '!=', ''),
    ]

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
        print(f"\n📊 Total de documentos encontrados: {len(documentos)}")

        # Agrupar según dimensiones activas
        duplicados = _agrupar_duplicados(documentos)

        return duplicados

    except Exception as e:
        print(f"❌ Error al buscar documentos: {e}")
        import traceback
        traceback.print_exc()
        return {}


def _build_key(doc):
    """Construye la clave de agrupación según la configuración activa."""
    partes = [doc.l10n_do_fiscal_number]
    if SOLO_MISMA_EMPRESA:
        partes.append(str(doc.company_id.id if doc.company_id else 'none'))
    if SOLO_MISMO_PARTNER:
        partes.append(str(doc.partner_id.id if doc.partner_id else 'none'))
    if SOLO_MISMO_TIPO:
        partes.append(doc.move_type)
    return '|'.join(partes)


def _agrupar_duplicados(documentos):
    """Agrupa documentos por clave compuesta y devuelve solo los grupos con más de uno."""
    grupos = defaultdict(list)
    for doc in documentos:
        grupos[_build_key(doc)].append(doc)

    duplicados = {}
    for key, docs in grupos.items():
        if len(docs) > 1:
            primer_doc = docs[0]
            duplicados[key] = {
                'numero_fiscal': primer_doc.l10n_do_fiscal_number,
                'company_id'   : primer_doc.company_id.id if primer_doc.company_id else None,
                'company_name' : primer_doc.company_id.name if primer_doc.company_id else 'Sin empresa',
                'partner_id'   : primer_doc.partner_id.id if primer_doc.partner_id else None,
                'move_type'    : primer_doc.move_type if SOLO_MISMO_TIPO else None,
                'documentos'   : docs,
            }
    return duplicados


# ============================================================
# MOSTRAR RESULTADOS
# ============================================================
def mostrar_duplicados(duplicados):
    """Muestra los grupos de duplicados de forma organizada."""

    if not duplicados:
        print("\n✅ ¡Excelente! No se encontraron números fiscales duplicados.")
        return

    print(f"\n⚠️  SE ENCONTRARON {len(duplicados)} GRUPOS DE NÚMEROS FISCALES DUPLICADOS\n")
    print("=" * 110)

    for key, data in sorted(duplicados.items(), key=lambda x: (
        x[1].get('company_name', ''),
        x[1]['numero_fiscal']
    )):
        numero_fiscal = data['numero_fiscal']
        documentos    = data['documentos']

        # Encabezado del grupo
        header = f"\n🔴 Número Fiscal: {numero_fiscal}"

        if SOLO_MISMA_EMPRESA and data.get('company_name'):
            header += f"  |  Empresa: {data['company_name']} (ID: {data['company_id']})"

        if SOLO_MISMO_PARTNER and data['partner_id']:
            partner_name = documentos[0].partner_id.name or 'Sin nombre'
            header += f"  |  Partner: {partner_name} (ID: {data['partner_id']})"

        if SOLO_MISMO_TIPO and data['move_type']:
            header += f"  |  Tipo: {TIPOS_DOCUMENTO.get(data['move_type'], data['move_type'])}"

        print(header)
        print(f"   Documentos en el grupo: {len(documentos)}")

        # Alertas cuando hay variación en dimensiones NO filtradas
        empresas_unicas = set(d.company_id.id if d.company_id else None for d in documentos)
        partners_unicos = set(d.partner_id.id if d.partner_id else None for d in documentos)
        tipos_unicos    = set(d.move_type for d in documentos)

        alertas = []
        if not SOLO_MISMA_EMPRESA and len(empresas_unicas) > 1:
            alertas.append(f"{len(empresas_unicas)} empresas distintas")
        if not SOLO_MISMO_PARTNER and len(partners_unicos) > 1:
            alertas.append(f"{len(partners_unicos)} partners distintos")
        if not SOLO_MISMO_TIPO and len(tipos_unicos) > 1:
            tipos_nombres = [TIPOS_DOCUMENTO.get(t, t) for t in tipos_unicos]
            alertas.append(f"tipos mezclados ({', '.join(tipos_nombres)})")

        if alertas:
            print(f"   ⚠️  ALERTA: {' + '.join(alertas)} — ¡REVISAR!")

        print("-" * 110)

        for i, doc in enumerate(documentos, 1):
            empresa      = doc.company_id.name if doc.company_id else 'Sin empresa'
            partner_name = doc.partner_id.name if doc.partner_id else 'Sin partner'
            tipo_doc     = TIPOS_DOCUMENTO.get(doc.move_type, doc.move_type)

            try:
                estado = dict(doc._fields['state'].selection).get(doc.state, doc.state)
            except Exception:
                estado = doc.state

            fecha = doc.invoice_date or 'Sin fecha'

            print(f"   {i}. ID: {doc.id:<8} | "
                  f"Empresa: {empresa:<25} | "
                  f"Tipo: {tipo_doc:<18} | "
                  f"Documento: {doc.name:<20} | "
                  f"Partner: {partner_name:<28} | "
                  f"Fecha: {fecha} | "
                  f"Monto: ${doc.amount_total:>12,.2f} | "
                  f"Estado: {estado}")

        print("-" * 110)

    # Resumen
    total_docs = sum(len(d['documentos']) for d in duplicados.values())
    print(f"\n📊 RESUMEN GENERAL:")
    print(f"   • Grupos de números fiscales duplicados : {len(duplicados)}")
    print(f"   • Total de documentos afectados         : {total_docs}")

    # Desglose por tipo
    contador_tipos = defaultdict(int)
    for data in duplicados.values():
        for doc in data['documentos']:
            contador_tipos[doc.move_type] += 1

    if contador_tipos:
        print(f"\n📋 DOCUMENTOS AFECTADOS POR TIPO:")
        for tipo, cantidad in sorted(contador_tipos.items()):
            print(f"   • {TIPOS_DOCUMENTO.get(tipo, tipo):<20}: {cantidad}")

    # Desglose por empresa (útil en multicompañía)
    if not SOLO_MISMA_EMPRESA or not FILTRAR_POR_COMPANIAS_ACTIVAS:
        contador_empresas = defaultdict(int)
        for data in duplicados.values():
            for doc in data['documentos']:
                nombre = doc.company_id.name if doc.company_id else 'Sin empresa'
                contador_empresas[nombre] += 1

        if len(contador_empresas) > 1:
            print(f"\n🏢 DOCUMENTOS AFECTADOS POR EMPRESA:")
            for empresa, cantidad in sorted(contador_empresas.items()):
                print(f"   • {empresa:<30}: {cantidad}")

    # Análisis crítico cuando no se filtra por empresa
    if not SOLO_MISMA_EMPRESA:
        grupos_misma_empresa = sum(
            1 for data in duplicados.values()
            if len(set(d.company_id.id if d.company_id else None
                       for d in data['documentos'])) == 1
        )
        grupos_dif_empresas = len(duplicados) - grupos_misma_empresa
        print(f"\n⚠️  ANÁLISIS MULTICOMPAÑÍA:")
        print(f"   • Duplicados dentro de la misma empresa   : {grupos_misma_empresa}")
        print(f"   • Duplicados entre empresas diferentes    : {grupos_dif_empresas}", end="")
        if grupos_dif_empresas > 0:
            print("  ← probables falsos positivos, considera activar SOLO_MISMA_EMPRESA")
        else:
            print()


# ============================================================
# EXPORTAR A CSV
# ============================================================
def exportar_a_csv(duplicados, filename='duplicados_fiscal.csv'):
    """Exporta los resultados a un archivo CSV."""
    import csv

    if not duplicados:
        print("No hay duplicados para exportar.")
        return

    fieldnames = [
        'numero_fiscal', 'company_id', 'company_nombre',
        'id_documento', 'tipo_documento', 'tipo_nombre', 'nombre_documento',
        'partner_id', 'partner_nombre', 'fecha', 'monto', 'estado', 'moneda',
    ]

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for key, data in sorted(duplicados.items(), key=lambda x: (
                x[1].get('company_name', ''), x[1]['numero_fiscal']
            )):
                for doc in data['documentos']:
                    try:
                        estado = dict(doc._fields['state'].selection).get(doc.state, doc.state)
                    except Exception:
                        estado = doc.state

                    writer.writerow({
                        'numero_fiscal'   : data['numero_fiscal'],
                        'company_id'      : doc.company_id.id if doc.company_id else '',
                        'company_nombre'  : doc.company_id.name if doc.company_id else '',
                        'id_documento'    : doc.id,
                        'tipo_documento'  : doc.move_type,
                        'tipo_nombre'     : TIPOS_DOCUMENTO.get(doc.move_type, doc.move_type),
                        'nombre_documento': doc.name,
                        'partner_id'      : doc.partner_id.id if doc.partner_id else '',
                        'partner_nombre'  : doc.partner_id.name if doc.partner_id else '',
                        'fecha'           : doc.invoice_date or '',
                        'monto'           : doc.amount_total,
                        'estado'          : estado,
                        'moneda'          : doc.currency_id.name if doc.currency_id else '',
                    })

        print(f"\n💾 Resultados exportados a: {filename}")

    except Exception as e:
        print(f"❌ Error al exportar a CSV: {e}")


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================
def main():
    duplicados = buscar_duplicados()
    mostrar_duplicados(duplicados)

    if duplicados:
        print("\n" + "=" * 110)
        try:
            respuesta = input("¿Deseas exportar los resultados a CSV? (s/n): ").lower()
        except EOFError:
            # Sin entrada interactiva (ej. odoo-bin shell < script.py)
            respuesta = 'n'
            print("\n(sin entrada interactiva, no se exporta)")
        if respuesta == 's':
            exportar_a_csv(duplicados)

    print("\n" + "=" * 110)
    print("✅ Proceso completado")
    print("=" * 110)


if __name__ == "__main__":
    main()