import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import generate_pbip_md as md
import generate_report_links as links
import tmdl_metadata as tmdl


class TmdlTests(unittest.TestCase):
    def parse(self, text):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'test.tmdl'
            path.write_text(text, encoding='utf-8')
            return tmdl.parse_tmdl_table(path)

    def test_multiline_dax_and_description(self):
        table = self.parse("""/// Table first line
/// Table second line
table Sales
    /// שורה ראשונה
    ///
    /// שורה שלישית
    measure 'Net Sales' =
            VAR amount = SUM(Sales[Amount])

            RETURN
                amount * 2
        formatString: #,0
        lineageTag: not-part-of-dax
    measure Next = 9
""")
        self.assertEqual(table['description'], 'Table first line\nTable second line')
        item = table['measures'][0]
        self.assertEqual(item['description'], 'שורה ראשונה\n\nשורה שלישית')
        self.assertEqual(item['expression'], 'VAR amount = SUM(Sales[Amount])\n\nRETURN\n    amount * 2')
        self.assertEqual(table['measures'][1]['expression'], '9')

    def test_property_description_continuations(self):
        table = self.parse("""table Sales
    measure Count = 1
        description: first line
            second line

            fourth line
        formatString: 0
    column ID
        dataType: int64
        description:
            column first
            column second
""")
        self.assertEqual(table['measures'][0]['description'], 'first line\nsecond line\n\nfourth line')
        self.assertEqual(table['columns'][0]['description'], 'column first\ncolumn second')
        self.assertIsNone(table['description'])

    def test_fenced_code_is_not_structure(self):
        table = self.parse("""table T
    measure 'Bob''s code' = ```
        VAR text = "start
measure fake = 100
description: not metadata
        end"

        RETURN text  
        ```
        formatString: 0
    measure Other = 2
""")
        self.assertEqual(len(table['measures']), 2)
        item = table['measures'][0]
        self.assertEqual(item['name'], "Bob's code")
        self.assertEqual(item['expression'], 'VAR text = "start\nmeasure fake = 100\ndescription: not metadata\nend"\n\nRETURN text  ')
        self.assertIsNone(item['description'])

    def test_calculated_columns_and_multiline_m(self):
        table = self.parse("""table T
    column 'שנה' =
            YEAR([Date])
        dataType: int64
    partition T = m
        mode: import
        source =
                let
                    Source = #table({"A"}, {{1}}),
                    Next = Source
                in
                    Next
    annotation Marker = not-code
""")
        self.assertEqual(table['calculated_columns'][0]['expression'], 'YEAR([Date])')
        self.assertEqual(table['partitions'][0]['expression'], 'let\n    Source = #table({"A"}, {{1}}),\n    Next = Source\nin\n    Next')

    def test_unclosed_fence_fails(self):
        with self.assertRaises(ValueError):
            self.parse('table T\n\tmeasure X = ```\nhello')

    def test_markdown_fence_keeps_literal_markup(self):
        value = '<svg>\n```\n</svg>'
        self.assertEqual(md.code_block(value, 'dax'), '````dax\n' + value + '\n````')

    def test_long_fenced_measure(self):
        body = '\n'.join(f'        VAR n{i} = {i}' for i in range(30))
        table = self.parse('table Example\n    measure Long = ```\n' + body + '\n        RETURN n29\n        ```\n        formatString: 0\n')
        value = table['measures'][0]['expression']
        self.assertEqual(len(value.splitlines()), 31)
        self.assertTrue(value.endswith('RETURN n29'))


class ReportTests(unittest.TestCase):
    def test_hebrew_field_reference(self):
        fields, _ = md.extract_visual_fields_and_filters({'Measure': {'Expression': {'SourceRef': {'Entity': 'מכירות'}}, 'Property': 'סכום מכירות'}})
        self.assertIn('מכירות.סכום מכירות', fields)

    def test_binding_and_duplicate_report_names(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for workspace in ('A', 'B'):
                report = root / workspace / 'Same.Report'
                model = root / workspace / 'Shared.SemanticModel'
                report.mkdir(parents=True)
                model.mkdir()
                (report / 'definition.pbir').write_text(json.dumps({'datasetReference': {'byPath': {'path': '../Shared.SemanticModel'}}}))
            with patch.object(md, 'repo_root', root):
                reports = md.find_reports(['A', 'B'])
            self.assertEqual([r['document'] for r in reports], ['A/Same.md', 'B/Same.md'])
            self.assertTrue(all(r['model_path'].name == 'Shared.SemanticModel' for r in reports))

    def test_invalid_json_does_not_silently_disappear(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'page.json'
            path.write_text('{broken')
            with self.assertRaises(json.JSONDecodeError):
                md.safe_json(path)


class LinkTests(unittest.TestCase):
    # Synthetic IDs generated only for isolated tests, never real service IDs.
    WID = links.guid('1' * 32)
    RID = links.guid('2' * 32)
    DID = links.guid('3' * 32)
    DOC = '# A\n\n## General\n- Report folder: `Dev/A.Report`\n\nPage ID: ReportSection123\n'

    def test_injection_is_idempotent_and_does_not_guess_dataset_workspace(self):
        report = dict(id=self.RID, datasetId=self.DID)
        once = links.enrich(self.DOC, report, self.WID)
        self.assertEqual(once, links.enrich(once, report, self.WID))
        self.assertIn('?pageName=ReportSection123', once)
        self.assertNotIn('Dataset workspace ID:', once)

    def test_removed_match_removes_stale_links(self):
        once = links.enrich(self.DOC, dict(id=self.RID), self.WID)
        removed = links.enrich(once, None, self.WID)
        self.assertNotIn('https://', removed)

    def test_page_text_inside_code_is_not_modified(self):
        doc = self.DOC + '```dax\nPage ID: fake\n```\n'
        output = links.enrich(doc, dict(id=self.RID), self.WID)
        self.assertNotIn('pageName=fake', output)

    def test_service_markers_inside_code_are_preserved(self):
        literal = '```dax\n<!-- service:start -->\ntext\n<!-- service:end -->\n```\n'
        output = links.enrich(self.DOC + literal, dict(id=self.RID), self.WID)
        self.assertIn(literal, output)
        self.assertEqual(output, links.enrich(output, dict(id=self.RID), self.WID))

    def test_ambiguous_names_get_no_link(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'A.md').write_text(self.DOC)
            manifest = [dict(name='A', source='Dev/A.Report', document='A.md', workspace='Dev')]
            inventory = {'Dev': [dict(name='A', id=self.RID), dict(name='A', id=self.DID)]}
            updates, missing = links.build_updates(root, manifest, {'Dev': self.WID}, inventory, {})
            self.assertEqual(missing, ['Dev/A.Report'])
            self.assertNotIn('https://', updates[root / 'A.md'])
            updates, missing = links.build_updates(root, manifest, {'Dev': self.WID}, inventory, {'Dev/A.Report': self.RID})
            self.assertEqual(missing, [])
            self.assertIn(self.RID, updates[root / 'A.md'])

    def test_pagination_rejects_external_host(self):
        with patch.object(links, 'request', return_value={'value': [], '@odata.nextLink': 'https://example.org/steal-token'}):
            with self.assertRaises(ValueError):
                links.list_reports(self.WID, 'secret')


if __name__ == '__main__':
    unittest.main()
