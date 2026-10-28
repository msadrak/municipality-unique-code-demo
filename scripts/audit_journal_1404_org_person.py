"""Independent read-only OOXML organizational formula and person audit.

No enrichment helpers are imported. Outputs are analytical evidence, never
approval, responsibility attribution, workbook changes or authoritative fixes.
"""
from __future__ import annotations
import argparse
import csv
import json
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from itertools import zip_longest
from pathlib import Path
import openpyxl

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
FILTER = 'فیلتر اسناد دارای سرفصل هزینه'
UNIT = 'واحد سازمانی'
DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')


def blank(v):
    return v is None or (isinstance(v, str) and not v.strip())


def canonical(v):
    # Preserve type distinctions: Excel exact lookup does not coerce text IDs.
    if v is None:
        return ('blank', '')
    if isinstance(v, (int, float)):
        return ('number', str(v))
    return ('text', str(v).casefold())


def native_scalar(text, kind):
    if text is None:
        return None
    if kind in ('s', 'inlineStr', 'str', 'e'):
        return text
    try:
        n = float(text)
        return int(n) if n.is_integer() else n
    except ValueError:
        return text


def shared_strings(z):
    if 'xl/sharedStrings.xml' not in z.namelist():
        return []
    root = ET.fromstring(z.read('xl/sharedStrings.xml'))
    return [''.join(t.text or '' for t in si.iter(NS + 't')) for si in root]


def journal_rows(path):
    with zipfile.ZipFile(path) as z:
        strings = shared_strings(z)
        # Resolve first worksheet through workbook relationships, not guessed ordering.
        rel = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        targets = {r.attrib['Id']: r.attrib['Target'] for r in rel}
        book = ET.fromstring(z.read('xl/workbook.xml'))
        sheet = book.find(NS + 'sheets')[0]
        rid = sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
        target = targets[rid]
        member = target.lstrip('/') if target.startswith('/') else 'xl/' + target
        with z.open(member) as f:
            # Remove completed row elements to keep memory bounded.
            context = ET.iterparse(f, events=('start', 'end'))
            _, root = next(context)
            for event, row in context:
                if event != 'end' or row.tag != NS + 'row':
                    continue
                rn = int(row.attrib['r'])
                values, formulas, errors = {}, {}, set()
                for cell in row:
                    address = cell.attrib.get('r', '')
                    col = re.match(r'[A-Z]+', address).group()
                    kind = cell.attrib.get('t', 'n')
                    ve = cell.find(NS + 'v')
                    text = ve.text if ve is not None else None
                    if kind == 's':
                        value = strings[int(text)] if text is not None else None
                    elif kind == 'inlineStr':
                        value = ''.join(t.text or '' for t in cell.iter(NS + 't'))
                    else:
                        value = native_scalar(text, kind)
                    values[col] = value
                    fe = cell.find(NS + 'f')
                    if fe is not None:
                        formulas[col] = {'text': fe.text or '', 'attributes': dict(fe.attrib)}
                    if kind == 'e':
                        errors.add(col)
                if rn >= 6:
                    yield rn, values, formulas, errors
                row.clear()
                root.clear()


def basic_name(v):
    return ' '.join(str(v or '').translate(DIGITS).replace('ي', 'ی').replace('ك', 'ک').replace('\u200c', ' ').replace('\xa0', ' ').split())


def punctuation_name(v):
    return ''.join(c for c in basic_name(v) if not c.isspace() and not unicodedata.category(c).startswith('P'))


def broad_name(v):
    return ''.join(c for c in punctuation_name(v).replace('آ', 'ا') if unicodedata.category(c) != 'Mn')


def dumps(v):
    return json.dumps(v, ensure_ascii=False, separators=(',', ':'))


def writer(path, fields):
    f = path.open('w', encoding='utf-8-sig', newline='')
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    return f, w


def audit(source, enriched, out):
    out.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.load_workbook(source, read_only=True, data_only=True)
    references = defaultdict(list)
    for rn, row in enumerate(wb[FILTER].values, 1):
        if rn >= 3 and not blank(row[0]):
            references[canonical(row[0])].append({'row': rn, 'key': row[0], 'region': row[1], 'document': row[2], 'unit': row[4]})
    units = defaultdict(list)
    for rn, row in enumerate(wb[UNIT].values, 1):
        if rn >= 3 and not blank(row[1]):
            units[canonical(row[1])].append({'row': rn, 'code': row[1], 'name': row[2]})
    wb.close()
    ambiguous = {k: rs for k, rs in references.items() if len({canonical(r['unit']) for r in rs}) > 1}
    fields = ['source_row', 'native_B_key', 'region', 'document_no', 'account', 'classification', 'formula_original', 'formula_enriched', 'formula_attributes', 'cached_original', 'cached_enriched', 'name_original', 'name_enriched', 'recomputed_result', 'evaluation_status', 'cached_status', 'recomputed_status', 'cached_recomputed_match', 'master_code_valid', 'master_name_valid', 'native_unit_master', 'first_filter_row', 'all_filter_matches', 'distinct_filter_units', 'document_lookup_ambiguous', 'same_B_different_E', 'independent_status', 'responsibility_warning']
    ff, fw = writer(out / 'Organizational_Unit_Formula_Audit.csv', fields)
    counts = Counter()
    people = defaultdict(lambda: defaultdict(list))
    person_changes = []
    shared_formulas = {}
    formula_pattern = re.compile(r"^=?VLOOKUP\(\$?B\$?(\d+),'" + re.escape(FILTER) + r"'!\$?A:\$?E,5,(?:0|FALSE)\)$", re.I)
    for left, right in zip_longest(journal_rows(source), journal_rows(enriched)):
        if left is None or right is None or left[0] != right[0]:
            raise ValueError('Source/enriched row populations differ')
        rn, v, forms, errors = left
        _, ev, eforms, eerrors = right
        counts['journal_rows'] += 1
        pid, name = v.get('AJ'), v.get('AK')
        if not blank(pid) and not blank(name):
            people[str(pid)][str(name)].append(rn)
            counts['person_pairs'] += 1
        elif not blank(pid) or not blank(name):
            people[str(pid) if pid is not None else ''][str(name) if name is not None else ''].append(rn)
            counts['person_incomplete_pairs'] += 1
        if (pid, name) != (ev.get('AJ'), ev.get('AK')):
            person_changes.append({'row': rn, 'original_id': pid, 'original_name': name, 'enriched_id': ev.get('AJ'), 'enriched_name': ev.get('AK')})
        if 'AD' not in forms:
            counts['absent_formula'] += 1
            counts['absent_formula_populated_code'] += not blank(v.get('AD'))
            continue
        counts['formula_rows'] += 1
        formula = forms['AD']['text']
        attrs = forms['AD']['attributes']
        if attrs.get('t') == 'shared':
            si = attrs.get('si')
            if formula:
                shared_formulas[si] = (rn, formula)
            elif si in shared_formulas:
                base_row, base_formula = shared_formulas[si]
                formula = re.sub(r'(\$?B)(\$?)(\d+)', lambda m: m.group(1) + m.group(2) + str(int(m.group(3)) if m.group(2) else int(m.group(3)) + rn - base_row), base_formula)
        match = formula_pattern.fullmatch(formula.strip())
        supported = match is not None and int(match.group(1)) == rn
        refs = references.get(canonical(v.get('B')), [])
        recomputed = (refs[0]['unit'] if not blank(refs[0]['unit']) else 0) if refs else '#N/A'
        if not supported:
            recomputed = None
        evaluation = 'EVALUATED_EXACT_FIRST_MATCH' if supported else 'UNSUPPORTED_FORMULA'
        counts[evaluation] += 1
        cached = v.get('AD')
        cached_status = 'ERROR' if 'AD' in errors else 'BLANK' if blank(cached) else 'VALUE'
        recomputed_status = 'NOT_EVALUATED' if not supported else 'ERROR' if not refs else 'VALUE'
        counts['cached_' + cached_status.lower()] += 1
        counts['recomputed_' + recomputed_status.lower()] += 1
        counts['recomputed_native_blank_return'] += supported and bool(refs) and blank(refs[0]['unit'])
        equal = supported and canonical(cached) == canonical(recomputed)
        counts['cached_recomputed_match' if equal else 'cached_recomputed_mismatch'] += 1
        master = units.get(canonical(recomputed), []) if supported else []
        code_valid = bool(master)
        name_valid = code_valid and any(basic_name(v.get('AE')) == basic_name(u['name']) for u in master)
        counts['valid_recomputed_code'] += code_valid
        counts['valid_recomputed_code_name_pair'] += name_valid
        counts['valid_cached_code'] += canonical(cached) in units
        counts['valid_cached_code_name_pair'] += any(basic_name(v.get('AE')) == basic_name(u['name']) for u in units.get(canonical(cached), []))
        amb = canonical(v.get('B')) in ambiguous
        counts['ambiguous_formula_rows'] += amb
        distinct = len({canonical(r['unit']) for r in refs})
        flags = []
        if not supported: flags.append('UNSUPPORTED_FORMULA')
        if not equal: flags.append('CACHE_MISMATCH')
        if not code_valid: flags.append('MASTER_CODE_INVALID')
        if not name_valid: flags.append('MASTER_NAME_INVALID')
        if amb: flags.append('MULTI_UNIT_DOCUMENT_AMBIGUITY')
        if forms.get('AD') != eforms.get('AD') or cached != ev.get('AD'): flags.append('SOURCE_ENRICHED_DIFFERENCE')
        fw.writerow(dict(zip(fields, [rn, v.get('B'), v.get('C'), v.get('E'), v.get('H'), v.get('X'), forms['AD']['text'], eforms.get('AD', {}).get('text'), dumps(attrs), cached, ev.get('AD'), v.get('AE'), ev.get('AE'), recomputed, evaluation, cached_status, recomputed_status, equal, code_valid, name_valid, dumps(master), refs[0]['row'] if refs else '', dumps(refs), distinct, amb, amb, '|'.join(flags) if flags else 'NATIVE_LOOKUP_CONSISTENT_NOT_RESPONSIBILITY_APPROVAL', 'First-match document lookup is computational only; document-level unit cannot establish line-level responsibility.'])))
    ff.close()
    pfields = ['exception_group', 'group_type', 'native_person_id', 'raw_name', 'normalized_name', 'source_rows', 'occurrences', 'all_id_variants', 'all_group_ids', 'category', 'independent_status', 'dated_evidence', 'required_decision']
    pf, pw = writer(out / 'Person_Master_Exceptions.csv', pfields)
    cf, cw = writer(out / 'proposed_person_corrections.csv', ['native_person_id', 'raw_name', 'proposed_analytical_name', 'source_rows', 'occurrences', 'scope', 'status', 'reason'])
    groups = []
    for pid, variants in sorted(people.items()):
        if len(variants) > 1:
            groups.append(('RAW_ID_VARIANTS', pid, [(pid, n) for n in variants]))
        if len({basic_name(n) for n in variants}) > 1:
            groups.append(('NORMALIZED_ID_VARIANTS', pid, [(pid, n) for n in variants]))
        if not pid or any(not n for n in variants):
            groups.append(('INCOMPLETE_PAIR', pid, [(pid, n) for n in variants]))
    byname = defaultdict(list)
    for pid, variants in people.items():
        for name in variants:
            if name: byname[broad_name(name)].append((pid, name))
    for name, pairs in sorted(byname.items()):
        if len({pid for pid, _ in pairs}) > 1:
            groups.append(('NORMALIZED_NAME_MULTIPLE_IDS', name, pairs))
    counts['raw_id_variant_groups'] = sum(t == 'RAW_ID_VARIANTS' for t, _, _ in groups)
    counts['normalized_id_variant_groups'] = sum(t == 'NORMALIZED_ID_VARIANTS' for t, _, _ in groups)
    counts['normalized_name_multiple_id_groups'] = sum(t == 'NORMALIZED_NAME_MULTIPLE_IDS' for t, _, _ in groups)
    legal_tokens = ('شرکت', 'سازمان', 'موسسه', 'اداره', 'بانک', 'شهرداری', 'تعاونی')
    for index, (typ, key, pairs) in enumerate(groups, 1):
        names = [n for _, n in pairs]
        if typ == 'INCOMPLETE_PAIR': category = 'MISSING_ID_OR_NAME'
        elif typ == 'NORMALIZED_NAME_MULTIPLE_IDS': category = 'POSSIBLE_WRONG_ID_OR_DISTINCT_PERSON_REQUIRES_MASTER'
        elif len({basic_name(n) for n in names}) == 1: category = 'PERSIAN_ARABIC_CHARACTERS_OR_WHITESPACE'
        elif len({punctuation_name(n) for n in names}) == 1: category = 'WHITESPACE_PUNCTUATION_VARIANT'
        elif len({''.join(c for c in punctuation_name(n) if unicodedata.category(c) != 'Cf') for n in names}) == 1: category = 'INVISIBLE_FORMAT_CHARACTER_VARIANT'
        elif len({broad_name(n) for n in names}) == 1: category = 'ALEF_MADDA_DIACRITICS_VARIANT_REVIEW'
        elif any(any(t in basic_name(n) for t in legal_tokens) for n in names): category = 'LEGAL_ENTITY_TEXTUAL_VARIANT_OR_WRONG_ID_REVIEW'
        else: category = 'SUBSTANTIVE_NAME_VARIANT_OR_WRONG_ID_REVIEW'
        counts['group_category_' + category] += 1
        ids = sorted({p for p, _ in pairs})
        for pid, name in pairs:
            rows = people[pid][name]
            pw.writerow(dict(zip(pfields, [f'PG-{index:05d}', typ, pid, name, basic_name(name), dumps(rows), len(rows), dumps({n: people[pid][n] for n in people[pid]}), dumps(ids), category, 'NORMALIZATION_ONLY_ANALYTICAL' if category == 'PERSIAN_ARABIC_CHARACTERS_OR_WHITESPACE' else 'REVIEW_REQUIRED', 'NONE_AVAILABLE_NO_LEGITIMATE_CHANGE_CLAIMED', 'Authoritative person master and dated legal/name-change evidence; no ID reassignment based on similarity.'])))
            counts['person_exception_csv_rows'] += 1
    for pid, variants in sorted(people.items()):
        for name, rows in sorted(variants.items()):
            proposed = basic_name(name)
            if name and proposed != name:
                cw.writerow({'native_person_id': pid, 'raw_name': name, 'proposed_analytical_name': proposed, 'source_rows': dumps(rows), 'occurrences': len(rows), 'scope': 'ANALYTICAL_DISPLAY_ONLY_ID_AND_RAW_SOURCE_UNCHANGED', 'status': 'NOT_AUTHORITATIVE_NOT_APPROVED', 'reason': 'Persian/Arabic Yeh/Kaf, digit glyph and whitespace standardization only; no punctuation, Alef/Madda, diacritic removal or legal-name substitution.'})
                counts['proposed_normalization_pairs'] += 1
                counts['proposed_normalization_occurrences'] += len(rows)
    pf.close()
    cf.close()
    counts['unique_person_ids'] = len(people)
    counts['unique_raw_person_pairs'] = sum(len(v) for v in people.values())
    counts['filter_keys'] = len(references)
    counts['filter_multi_unit_keys'] = len(ambiguous)
    counts['person_source_enriched_changed_rows'] = len(person_changes)
    metrics = {'counts': dict(counts), 'formula_coverage': counts['EVALUATED_EXACT_FIRST_MATCH'] / counts['formula_rows'] if counts['formula_rows'] else 1, 'row_reconciliation': counts['formula_rows'] + counts['absent_formula'] == counts['journal_rows'], 'person_occurrence_reconciliation': sum(len(rs) for names in people.values() for rs in names.values()) == counts['person_pairs'] + counts['person_incomplete_pairs'], 'prior_reported_normalized_groups': 37, 'normalized_groups_reconcile_prior_37': counts['normalized_id_variant_groups'] == 37, 'source': str(source), 'enriched': str(enriched), 'filter_ambiguities': [{'native_B_key': rs[0]['key'], 'native_filter_rows': rs} for rs in ambiguous.values()], 'person_source_enriched_changes': person_changes, 'governance': 'Native lookup consistency does not approve responsibility. No person master or dated change evidence available in supplied workbooks. No source/deliverable modifications. Normalization proposals are analytical only.', 'method': 'Independent OOXML XML element row parsing of both workbooks; exact type-sensitive first-match VLOOKUP with native filter A/E and unit master B/C. Cached original/enriched and recomputed results retained separately. All person IDs/raw variants retain complete source row lists.'}
    (out / 'org_person_metrics.json').write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'counts': dict(counts), 'formula_coverage': metrics['formula_coverage'], 'row_reconciliation': metrics['row_reconciliation'], 'person_occurrence_reconciliation': metrics['person_occurrence_reconciliation'], 'outputs': [str(out / n) for n in ['Organizational_Unit_Formula_Audit.csv', 'Person_Master_Exceptions.csv', 'org_person_metrics.json', 'proposed_person_corrections.csv']]}, ensure_ascii=False, indent=2))

def finalize_metrics(out):
    """Reconcile emitted evidence without reopening or changing workbooks."""
    metric_path = out / 'org_person_metrics.json'
    metrics = json.loads(metric_path.read_text(encoding='utf-8'))
    counts = metrics['counts']
    exception_path = out / 'Person_Master_Exceptions.csv'
    with exception_path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        exception_fields = reader.fieldnames
        exceptions = list(reader)
    categories = defaultdict(set)
    for row in exceptions:
        if row['group_type'] in ('RAW_ID_VARIANTS', 'NORMALIZED_ID_VARIANTS'):
            names = json.loads(row['all_id_variants'])
            if len({''.join(c for c in punctuation_name(n) if unicodedata.category(c) != 'Cf') for n in names}) == 1:
                row['category'] = 'INVISIBLE_FORMAT_CHARACTER_VARIANT'
                row['independent_status'] = 'NORMALIZATION_ONLY_ANALYTICAL_NO_IDENTITY_APPROVAL'
        categories[row['category']].add(row['exception_group'])
    ef, ew = writer(exception_path, exception_fields)
    ew.writerows(exceptions)
    ef.close()
    for key in list(counts):
        if key.startswith('group_category_'):
            del counts[key]
    counts.update({'group_category_' + k: len(v) for k, v in categories.items()})
    strict = 0
    cached_strict = 0
    exact_name_pairs = 0
    document_numbers = defaultdict(set)
    with (out / 'Organizational_Unit_Formula_Audit.csv').open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            document_numbers[row['native_B_key']].add(row['document_no'])
            good = row['master_code_valid'] == 'True' and any(row['name_original'] == str(u['name']) for u in json.loads(row['native_unit_master']))
            exact_name_pairs += good
            strict += good and row['document_lookup_ambiguous'] == 'False'
            cached_strict += good and row['document_lookup_ambiguous'] == 'False' and row['cached_recomputed_match'] == 'True'
    counts['valid_recomputed_code_and_name_raw_exact'] = exact_name_pairs
    counts['valid_recomputed_code_and_name'] = cached_strict
    counts['valid_recomputed_code_and_name_excluding_ambiguous_document'] = strict
    counts['valid_cached_recomputed_code_and_name_excluding_ambiguous_document'] = cached_strict
    metrics['eligibility_caveat'] = 'Strict counts exclude multi-unit native filter keys but do not establish line-level responsibility approval.'
    metrics['formula_B_keys_differing_journal_document_E'] = {k: sorted(v) for k, v in document_numbers.items() if len(v) > 1}
    cohorts = defaultdict(lambda: {'groups': set(), 'rows': set(), 'categories': Counter()})
    substantive_rows, harmless_rows, orthographic_review_rows = set(), set(), set()
    normalized_candidates = {}
    with (out / 'Person_Master_Exceptions.csv').open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            typ = row['group_type']
            cohort = cohorts[typ]
            cohort['groups'].add(row['exception_group'])
            rows = json.loads(row['source_rows'])
            cohort['rows'].update(rows)
            cohort['categories'][row['category']] += 1
            if typ == 'NORMALIZED_ID_VARIANTS':
                normalized_candidates[(row['native_person_id'], row['raw_name'])] = row
            if typ == 'RAW_ID_VARIANTS':
                target = harmless_rows if row['category'] in ('PERSIAN_ARABIC_CHARACTERS_OR_WHITESPACE', 'WHITESPACE_PUNCTUATION_VARIANT', 'INVISIBLE_FORMAT_CHARACTER_VARIANT') else substantive_rows
                if row['category'] == 'ALEF_MADDA_DIACRITICS_VARIANT_REVIEW':
                    target = orthographic_review_rows
                target.update(rows)
    metrics['person_cohorts'] = {k: {'groups': len(v['groups']), 'unique_affected_rows': len(v['rows']), 'variant_csv_rows_by_category': dict(v['categories'])} for k, v in cohorts.items()}
    counts['same_id_substantive_variant_affected_rows'] = len(substantive_rows)
    counts['same_id_harmless_variant_affected_rows'] = len(harmless_rows)
    counts['same_id_alef_diacritics_review_affected_rows'] = len(orthographic_review_rows)
    proposal_path = out / 'proposed_person_corrections.csv'
    with proposal_path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        proposal_fields = reader.fieldnames
        proposals = list(reader)
    present = {(r['native_person_id'], r['raw_name']) for r in proposals}
    for key, row in normalized_candidates.items():
        if key in present:
            continue
        proposals.append({'native_person_id': row['native_person_id'], 'raw_name': row['raw_name'], 'proposed_analytical_name': row['normalized_name'], 'source_rows': row['source_rows'], 'occurrences': row['occurrences'], 'scope': 'ANALYTICAL_DISPLAY_ONLY_ID_AND_RAW_SOURCE_UNCHANGED', 'status': 'NO_IDENTITY_CORRECTION_PROPOSED_REVIEW_REQUIRED', 'reason': 'Included for complete original37 cohort; normalization unchanged or insufficient to resolve substantive variants. No merge, reassignment or legal-name change authorized.'})
    pf, pw = writer(proposal_path, proposal_fields)
    pw.writerows(proposals)
    pf.close()
    counts['proposed_corrections_csv_rows'] = len(proposals)
    counts['normalized_conflict_candidate_pairs'] = len(normalized_candidates)
    taxonomy_groups = defaultdict(list)
    for row in exceptions:
        if row['group_type'] == 'NORMALIZED_ID_VARIANTS':
            taxonomy_groups[row['exception_group']].append(row)
    legal_tokens = ('شرکت', 'سازمان', 'موسسه', 'اداره', 'بانک', 'شهرداری', 'تعاونی')
    overlays = defaultdict(list)
    disjoint = Counter()
    for group, records in taxonomy_groups.items():
        names = [r['raw_name'] for r in records]
        category = records[0]['category']
        disjoint[category] += 1
        evidence = {'group': group, 'native_person_id': records[0]['native_person_id'], 'disjoint_category': category, 'variants': [{'raw_name': r['raw_name'], 'source_rows': json.loads(r['source_rows']), 'occurrences': int(r['occurrences'])} for r in records]}
        if any(any(t in basic_name(n) for t in legal_tokens) for n in names):
            overlays['legal_entity_textual_variants'].append(evidence)
        if len({basic_name(n) for n in names}) < len(set(names)):
            overlays['persian_arabic_characters_or_whitespace'].append(evidence)
        if len({punctuation_name(n) for n in names}) < len({basic_name(n) for n in names}):
            overlays['whitespace_or_punctuation'].append(evidence)
        if category == 'INVISIBLE_FORMAT_CHARACTER_VARIANT':
            overlays['invisible_format_characters'].append(evidence)
        if category == 'ALEF_MADDA_DIACRITICS_VARIANT_REVIEW':
            overlays['alef_madda_or_diacritics'].append(evidence)
    taxonomy = {'cohort': 'Original37 normalized native-ID name variant groups', 'groups': len(taxonomy_groups), 'disjoint_category_group_counts': dict(disjoint), 'overlays': {k: {'groups': len(overlays[k]), 'evidence': overlays[k]} for k in ('legal_entity_textual_variants', 'persian_arabic_characters_or_whitespace', 'whitespace_or_punctuation', 'invisible_format_characters', 'alef_madda_or_diacritics')}, 'proven_legitimate_dated_changes': 0, 'proven_wrong_id_associations': 0, 'potential_wrong_association': 'Unproven; name similarity alone cannot establish identity or wrong association', 'separate_normalized_name_multiple_id_groups': counts['normalized_name_multiple_id_groups'], 'caveat': 'Overlay counts overlap, not additive. Legal entity overlay describes entity text, not a proven legal-name change. No dated identity evidence exists in supplied workbooks.'}
    metrics['person_variant_taxonomy'] = taxonomy
    (out / 'person_variant_taxonomy.json').write_text(json.dumps(taxonomy, ensure_ascii=False, indent=2), encoding='utf-8')
    metric_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding='utf-8')
    print(dumps({'additional_counts': counts, 'person_cohorts': metrics['person_cohorts']}))



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('C:/Users/sadra/Desktop/دفتر روزنامه 1404 - با اشخاص جدید.xlsx'))
    parser.add_argument('--enriched', type=Path, default=Path('data/deliverables/journal_1404_enrichment_final/Accounting_Journal_1404_Desired_State_Enriched_v1.xlsx'))
    parser.add_argument('--out', type=Path, default=Path('data/deliverables/journal_1404_enrichment_v1_independent_audit'))
    args = parser.parse_args()
    audit(args.source, args.enriched, args.out)
    finalize_metrics(args.out)
