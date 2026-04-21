"""
Service d'export Excel pour les paiements de transport
"""

from decimal import Decimal
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
from django.http import HttpResponse
from .services import TransportService


def _to_num(value):
    """Convertit Decimal en float pour openpyxl."""
    if isinstance(value, Decimal):
        return float(value)
    return value


class ExcelExport:
    """
    Générateur d'export Excel pour les transports
    """
    
    # Styles
    HEADER_FILL = PatternFill(start_color="0A2D6E", end_color="0A2D6E", fill_type="solid")
    HEADER_FONT = Font(color="FFFFFF", bold=True)
    ACCENT_FILL = PatternFill(start_color="FFB800", end_color="FFB800", fill_type="solid")
    ACCENT_FONT = Font(color="0A2D6E", bold=True)
    SUCCESS_FILL = PatternFill(start_color="22C55E", end_color="22C55E", fill_type="solid")
    DANGER_FILL = PatternFill(start_color="EF4444", end_color="EF4444", fill_type="solid")
    BORDER = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    @staticmethod
    def export_openers(date_debut, date_fin):
        """
        Exporte les données des openers pour la semaine donnée
        """
        wb = Workbook()
        
        # Supprimer la feuille par défaut
        wb.remove(wb.active)
        
        # Créer les feuilles
        ws_resume = wb.create_sheet("Résumé Openers")
        ws_detail = wb.create_sheet("Détail Openers")
        
        # Récupérer les données
        data = TransportService.calcul_openers_semaine(date_debut, date_fin)
        
        # En-tête du fichier
        ExcelExport._add_header(ws_resume, "Openers", date_debut, date_fin)
        ExcelExport._add_header(ws_detail, "Openers - Détail journalier", date_debut, date_fin)
        
        # Feuille Résumé
        headers = ["Agent", "Equipe", "Team", "Objectif", "Seuil", "Realisation", "Taux (%)", "Transport base", "Transport net", "Statut"]
        ExcelExport._add_table(ws_resume, headers, data['agents'], 5, {
            'Agent': lambda a: a['agent'].numero,
            'Equipe': lambda a: a['agent'].equipe or '-',
            'Team': lambda a: a['agent'].team or '-',
            'Objectif': lambda a: a['objectif'],
            'Seuil': lambda a: a['seuil'],
            'Realisation': lambda a: a['realisation'],
            'Taux (%)': lambda a: _to_num(a['taux']),
            'Transport base': lambda a: _to_num(a['transport_base']),
            'Transport net': lambda a: _to_num(a['transport_net']),
            'Statut': lambda a: a['statut'],
        })
        
        # Ajouter les totaux
        row = ws_resume.max_row + 2
        ws_resume.cell(row=row, column=1, value="TOTAUX").font = Font(bold=True)
        ws_resume.cell(row=row, column=6, value=sum(a['realisation'] for a in data['agents']))
        ws_resume.cell(row=row, column=9, value=data['total_transport'])
        ws_resume.cell(row=row, column=9).number_format = '#,##0'
        
        # Feuille Détail
        current_row = 5
        for agent_data in data['agents']:
            agent = agent_data['agent']
            jours = TransportService.get_detail_journalier_opener(agent, date_debut, date_fin)
            
            # En-tête de section
            ws_detail.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=5)
            cell = ws_detail.cell(row=current_row, column=1, value=f"Agent: {agent.numero} - Équipe: {agent.equipe} - Team: {agent.team or 'Sans team'}")
            cell.font = ExcelExport.ACCENT_FONT
            cell.fill = ExcelExport.ACCENT_FILL
            current_row += 1
            
            # Sous-en-tête
            sub_headers = ["Jour", "Date", "Réalisation"]
            for col, header in enumerate(sub_headers, 1):
                cell = ws_detail.cell(row=current_row, column=col, value=header)
                cell.font = ExcelExport.HEADER_FONT
                cell.fill = ExcelExport.HEADER_FILL
                cell.border = ExcelExport.BORDER
            current_row += 1
            
            # Données journalières
            for jour in jours:
                ws_detail.cell(row=current_row, column=1, value=jour['jour_semaine'])
                ws_detail.cell(row=current_row, column=2, value=jour['date'].strftime('%d/%m/%Y'))
                ws_detail.cell(row=current_row, column=3, value=jour['realisation'])
                current_row += 1
            
            # Ligne de total
            ws_detail.cell(row=current_row, column=1, value="TOTAL").font = Font(bold=True)
            ws_detail.cell(row=current_row, column=3, value=agent_data['realisation'])
            current_row += 2
        
        # Ajuster les largeurs de colonnes
        ExcelExport._auto_width(ws_resume)
        ExcelExport._auto_width(ws_detail)
        
        # Générer la réponse HTTP
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"transport_openers_{date_debut.strftime('%Y%m%d')}_{date_fin.strftime('%Y%m%d')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        
        return response
    
    @staticmethod
    def export_animateurs(date_debut, date_fin):
        """
        Exporte les données des animateurs pour la semaine donnée
        """
        wb = Workbook()
        
        # Supprimer la feuille par défaut
        wb.remove(wb.active)
        
        # Créer les feuilles
        ws_resume = wb.create_sheet("Résumé Animateurs")
        ws_detail = wb.create_sheet("Détail Animateurs")
        
        # Récupérer les données
        data = TransportService.calcul_animateurs_semaine(date_debut, date_fin)
        
        # En-tête du fichier
        ExcelExport._add_header(ws_resume, "Animateurs", date_debut, date_fin)
        ExcelExport._add_header(ws_detail, "Animateurs - Détail journalier", date_debut, date_fin)
        
        # Feuille Résumé
        headers = ["Agent", "Volume realise (FCFA)", "Transport a payer (FCFA)"]
        ExcelExport._add_table(ws_resume, headers, data['agents'], 5, {
            'Agent': lambda a: a['agent'].numero,
            'Volume realise (FCFA)': lambda a: _to_num(a['volume_realise']),
            'Transport a payer (FCFA)': lambda a: _to_num(a['transport']),
        })

        # Ajouter les totaux
        row = ws_resume.max_row + 2
        ws_resume.cell(row=row, column=1, value="TOTAUX").font = Font(bold=True)
        ws_resume.cell(row=row, column=2, value=_to_num(sum(a['volume_realise'] for a in data['agents'])))
        ws_resume.cell(row=row, column=3, value=_to_num(data['total_transport']))
        ws_resume.cell(row=row, column=2).number_format = '#,##0'
        ws_resume.cell(row=row, column=3).number_format = '#,##0'
        
        # Feuille Détail
        current_row = 5
        for agent_data in data['agents']:
            agent = agent_data['agent']
            jours = TransportService.get_detail_journalier_animateur(agent, date_debut, date_fin)
            
            # En-tête de section
            ws_detail.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=4)
            cell = ws_detail.cell(row=current_row, column=1, value=f"Agent: {agent.numero}")
            cell.font = ExcelExport.ACCENT_FONT
            cell.fill = ExcelExport.ACCENT_FILL
            current_row += 1
            
            # Sous-en-tête
            sub_headers = ["Jour", "Date", "Volume (FCFA)", "Transport (FCFA)"]
            for col, header in enumerate(sub_headers, 1):
                cell = ws_detail.cell(row=current_row, column=col, value=header)
                cell.font = ExcelExport.HEADER_FONT
                cell.fill = ExcelExport.HEADER_FILL
                cell.border = ExcelExport.BORDER
            current_row += 1
            
            # Données journalières
            for jour in jours:
                ws_detail.cell(row=current_row, column=1, value=jour['jour_semaine'])
                ws_detail.cell(row=current_row, column=2, value=jour['date'].strftime('%d/%m/%Y'))
                ws_detail.cell(row=current_row, column=3, value=_to_num(jour['volume']))
                ws_detail.cell(row=current_row, column=4, value=_to_num(jour['transport']))
                ws_detail.cell(row=current_row, column=3).number_format = '#,##0'
                ws_detail.cell(row=current_row, column=4).number_format = '#,##0'
                current_row += 1

            # Ligne de total
            ws_detail.cell(row=current_row, column=1, value="TOTAL").font = Font(bold=True)
            ws_detail.cell(row=current_row, column=3, value=_to_num(agent_data['volume_realise']))
            ws_detail.cell(row=current_row, column=4, value=_to_num(agent_data['transport']))
            ws_detail.cell(row=current_row, column=3).number_format = '#,##0'
            ws_detail.cell(row=current_row, column=4).number_format = '#,##0'
            current_row += 2
        
        # Ajuster les largeurs de colonnes
        ExcelExport._auto_width(ws_resume)
        ExcelExport._auto_width(ws_detail)
        
        # Générer la réponse HTTP
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"transport_animateurs_{date_debut.strftime('%Y%m%d')}_{date_fin.strftime('%Y%m%d')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        
        return response
    
    @staticmethod
    def _add_header(ws, title, date_debut, date_fin):
        """
        Ajoute l'en-tête du fichier Excel
        """
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=5)
        cell = ws.cell(row=1, column=1, value=f"MixxPay Agents - Rapport Transport {title}")
        cell.font = Font(size=14, bold=True, color="0A2D6E")
        
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=5)
        cell = ws.cell(row=2, column=1, value=f"Période: du {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}")
        cell.font = Font(size=11)
        
        ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=5)
        cell = ws.cell(row=3, column=1, value=f"Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
        cell.font = Font(size=10, color="64748B")
    
    @staticmethod
    def _add_table(ws, headers, data, start_row, value_getters):
        """
        Ajoute un tableau structuré dans la feuille Excel
        """
        # En-têtes
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=start_row, column=col, value=header)
            cell.font = ExcelExport.HEADER_FONT
            cell.fill = ExcelExport.HEADER_FILL
            cell.border = ExcelExport.BORDER
            cell.alignment = Alignment(horizontal='center')
        
        # Données
        current_row = start_row + 1
        for item in data:
            for col, (header, getter) in enumerate(value_getters.items(), 1):
                value = getter(item)
                cell = ws.cell(row=current_row, column=col, value=value)
                cell.border = ExcelExport.BORDER
                
                # Formater les nombres
                if isinstance(value, (int, float, Decimal)) and header not in ['Agent', 'Equipe', 'Equipe', 'Team', 'Statut']:
                    cell.number_format = '#,##0'

                # Colorer le statut
                if header == 'Statut' and value == 'Atteint':
                    cell.fill = ExcelExport.SUCCESS_FILL
                elif header == 'Statut' and value == 'Non atteint':
                    cell.fill = ExcelExport.DANGER_FILL
            
            current_row += 1
    
    @staticmethod
    def _auto_width(ws):
        """
        Ajuste automatiquement la largeur des colonnes
        """
        for column in ws.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 30)
            ws.column_dimensions[column_letter].width = adjusted_width