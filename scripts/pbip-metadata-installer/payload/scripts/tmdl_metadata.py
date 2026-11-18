"""Read documentation-relevant TMDL, respecting indentation and fenced expressions.

This is a metadata reader, not a replacement for Microsoft's TMDL validator.
Unknown properties remain available in the source TMDL files.
"""
import re
import textwrap


DECL = re.compile(r"^(?P<kind>table|column|measure|partition|hierarchy|calculationItem|calculatedColumn)\s+(?:'(?P<quoted>(?:[^']|'')*)'|(?P<plain>[^=]+?))\s*(?:=\s*(?P<value>.*))?$")


def indent(line):
    return len(line.expandtabs(4)) - len(line.expandtabs(4).lstrip())


def declaration(line):
    match = DECL.match(line.strip())
    if not match:
        return None
    kind, quoted, plain, value = match.group('kind', 'quoted', 'plain', 'value')
    return kind, quoted.replace("''", "'") if quoted is not None else plain.strip(), value


def structural_lines(text):
    """Yield only TMDL structure; never interpret fenced code as declarations."""
    fenced = False
    for index, line in enumerate(text.splitlines()):
        if fenced:
            if line.strip() == '```':
                fenced = False
            continue
        yield index, line
        if re.search(r'[=:]\s*```\s*$', line):
            fenced = True
    if fenced:
        raise ValueError('Unclosed TMDL expression fence')


def leading_description(lines, index):
    result = []
    level = indent(lines[index])
    index -= 1
    while index >= 0 and lines[index].lstrip().startswith('///') and indent(lines[index]) == level:
        value = lines[index].lstrip()[3:]
        result.append(value[1:] if value.startswith(' ') else value)
        index -= 1
    return '\n'.join(reversed(result)) if result else None


def read_value(lines, index, value, property_level):
    """Read until a sibling property. A fence's closing indent is its boundary."""
    if value.strip() == '```':
        collected = []
        for line in lines[index + 1:]:
            if line.strip() == '```':
                boundary = indent(line)
                return '\n'.join(x.expandtabs(4)[boundary:] if indent(x) >= boundary else x.expandtabs(4) for x in collected)
            collected.append(line)
        raise ValueError('Unclosed TMDL expression fence')
    tail = []
    for line in lines[index + 1:]:
        if line.strip() and indent(line) <= property_level:
            break
        tail.append(line.expandtabs(4))
    trailing = textwrap.dedent('\n'.join(tail)).strip('\n').rstrip()
    first = value.strip()
    return '\n'.join(x for x in (first, trailing) if x) or None


def parse_multiline_property(block_text, key):
    lines = block_text.splitlines()
    if not lines:
        return None
    # Properties directly beneath the owning declaration, not child-object properties.
    level = indent(lines[0]) + 4
    for index, line in structural_lines(block_text):
        if indent(line) != level:
            continue
        match = re.match(rf'^[ \t]*{re.escape(key)}[ \t]*[:=][ \t]*(.*)$', line, re.I)
        if match:
            return read_value(lines, index, match.group(1), level)
    return None


def parse_inline_property(block_text, key):
    return parse_multiline_property(block_text, key)


def parse_description(block_text, doc_comment=None):
    return doc_comment if doc_comment is not None else parse_multiline_property(block_text, 'description')


def expression(block):
    lines = block.splitlines()
    decl = declaration(lines[0])
    if decl and decl[2] is not None:
        return read_value(lines, 0, decl[2], indent(lines[0]) + 4)
    return parse_multiline_property(block, 'expression')


def table_objects(text):
    lines = text.splitlines()
    structure = list(structural_lines(text))
    table = next(((i, line) for i, line in structure if declaration(line) and declaration(line)[0] == 'table'), None)
    if table is None:
        raise ValueError('No table declaration in TMDL')
    table_index, table_line = table
    level = indent(table_line) + 4
    children = [(i, line) for i, line in structure if indent(line) == level and declaration(line)]
    results = []
    for index, line in children:
        end = index + 1
        # Use structure rather than raw lines: fenced expressions can be unindented.
        end = next((i for i, following in structure if i > index and following.strip() and indent(following) <= level), len(lines))
        results.append((declaration(line), '\n'.join(lines[index:end]), leading_description(lines, index)))
    first_child = next((i for i, line in structure if i > table_index and line.strip() and indent(line) == level and declaration(line)), len(lines))
    header = '\n'.join(lines[table_index:first_child])
    return declaration(table_line)[1], parse_description(header, leading_description(lines, table_index)), results


def parse_tmdl_table(table_file):
    text = table_file.read_text(encoding='utf-8-sig')
    name, description, objects = table_objects(text)
    result = dict(table_name=name, description=description, columns=[], calculated_columns=[], measures=[], partitions=[], hierarchies=[])
    for (kind, name, value), block, doc in objects:
        desc = parse_description(block, doc)
        if kind in ('column', 'calculatedColumn'):
            item = dict(name=name, data_type=parse_inline_property(block, 'dataType'), description=desc)
            if value is not None or kind == 'calculatedColumn':
                item['expression'] = expression(block)
                result['calculated_columns'].append(item)
            else:
                result['columns'].append(item)
        elif kind == 'measure':
            result['measures'].append(dict(name=name, description=desc, expression=expression(block), display_folder=parse_inline_property(block, 'displayFolder'), format_string=parse_inline_property(block, 'formatString')))
        elif kind == 'partition':
            source = parse_multiline_property(block, 'source') or parse_multiline_property(block, 'query')
            # Entity sources have a nested source block instead of an expression.
            nested = re.search(r'^[ \t]*source[ \t]*\n(?P<body>(?:[ \t]+.*\n?)*)', block, re.M)
            entity = re.search(r'^\s*entityName:\s*(.+)$', nested.group('body'), re.M) if nested else None
            origin = re.search(r'^\s*expressionSource:\s*(.+)$', nested.group('body'), re.M) if nested else None
            result['partitions'].append(dict(name=name, kind=value, mode=parse_inline_property(block, 'mode'), expression=source, entity_name=entity.group(1) if entity else None, expression_source=origin.group(1) if origin else None))
        elif kind == 'hierarchy':
            result['hierarchies'].append(dict(name=name))
    return result
