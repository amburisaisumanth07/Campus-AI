import React from 'react';

interface MarkdownRendererProps {
  content: string;
}

/**
 * Parse and render inline markdown elements:
 * - **bold** or __bold__
 * - *italic* or _italic_
 * - `code`
 * - [text](url)
 */
export const renderInlineMarkdown = (text: string): React.ReactNode => {
  if (!text) return text;

  // Tokenize regex for inline elements
  const tokens: React.ReactNode[] = [];
  let remaining = text;
  let keyIndex = 0;

  // Pattern matching: inline code, links, bold, italic
  const inlineRegex = /(`[^`]+`)|(\[[^\]]+\]\([^)]+\))|(\*\*[^*]+\*\*)|(__[^_]+__)|(\*[^*]+\*)|(_[^_]+_)/;

  while (remaining) {
    const match = remaining.match(inlineRegex);
    if (!match || match.index === undefined) {
      tokens.push(remaining);
      break;
    }

    // Text before match
    if (match.index > 0) {
      tokens.push(remaining.substring(0, match.index));
    }

    const matchedStr = match[0];
    keyIndex++;

    if (matchedStr.startsWith('`') && matchedStr.endsWith('`')) {
      // Inline code
      tokens.push(
        <code key={`code-${keyIndex}`} className="markdown-inline-code">
          {matchedStr.slice(1, -1)}
        </code>
      );
    } else if (matchedStr.startsWith('[') && matchedStr.includes('](')) {
      // Link
      const linkTextMatch = matchedStr.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (linkTextMatch) {
        tokens.push(
          <a
            key={`link-${keyIndex}`}
            href={linkTextMatch[2]}
            target="_blank"
            rel="noopener noreferrer"
            className="markdown-link"
          >
            {linkTextMatch[1]}
          </a>
        );
      } else {
        tokens.push(matchedStr);
      }
    } else if (
      (matchedStr.startsWith('**') && matchedStr.endsWith('**')) ||
      (matchedStr.startsWith('__') && matchedStr.endsWith('__'))
    ) {
      // Bold
      const inner = matchedStr.slice(2, -2);
      tokens.push(
        <strong key={`bold-${keyIndex}`} className="markdown-strong">
          {renderInlineMarkdown(inner)}
        </strong>
      );
    } else if (
      (matchedStr.startsWith('*') && matchedStr.endsWith('*')) ||
      (matchedStr.startsWith('_') && matchedStr.endsWith('_'))
    ) {
      // Italic
      const inner = matchedStr.slice(1, -1);
      tokens.push(
        <em key={`em-${keyIndex}`} className="markdown-em">
          {renderInlineMarkdown(inner)}
        </em>
      );
    } else {
      tokens.push(matchedStr);
    }

    remaining = remaining.substring(match.index + matchedStr.length);
  }

  return tokens.length === 1 && typeof tokens[0] === 'string' ? tokens[0] : <>{tokens}</>;
};

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  if (!content || !content.trim()) {
    return null;
  }

  const lines = content.split('\n');
  const blocks: React.ReactNode[] = [];
  let currentBlockIndex = 0;

  let i = 0;
  while (i < lines.length) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();

    // 1. Code Block (```)
    if (trimmed.startsWith('```')) {
      const codeLang = trimmed.slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // Skip closing ```
      blocks.push(
        <div key={`codeblock-${currentBlockIndex++}`} className="markdown-code-block-container">
          {codeLang && <div className="code-block-header">{codeLang}</div>}
          <pre className="markdown-code-pre">
            <code>{codeLines.join('\n')}</code>
          </pre>
        </div>
      );
      continue;
    }

    // 2. Horizontal Rule (---, ***, ___)
    if (/^(\-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      blocks.push(<hr key={`hr-${currentBlockIndex++}`} className="markdown-divider" />);
      i++;
      continue;
    }

    // 3. Headings (# ... ####)
    const headingMatch = rawLine.match(/^(#{1,6})\s+(.*)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const headingText = headingMatch[2];
      const inline = renderInlineMarkdown(headingText);

      switch (level) {
        case 1:
          blocks.push(<h1 key={`h1-${currentBlockIndex++}`} className="markdown-h1">{inline}</h1>);
          break;
        case 2:
          blocks.push(<h2 key={`h2-${currentBlockIndex++}`} className="markdown-h2">{inline}</h2>);
          break;
        case 3:
          blocks.push(<h3 key={`h3-${currentBlockIndex++}`} className="markdown-h3">{inline}</h3>);
          break;
        case 4:
          blocks.push(<h4 key={`h4-${currentBlockIndex++}`} className="markdown-h4">{inline}</h4>);
          break;
        default:
          blocks.push(<h5 key={`h5-${currentBlockIndex++}`} className="markdown-h5">{inline}</h5>);
          break;
      }
      i++;
      continue;
    }

    // 4. Blockquote (> ...)
    if (trimmed.startsWith('>')) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('>')) {
        quoteLines.push(lines[i].trim().replace(/^>\s*/, ''));
        i++;
      }
      blocks.push(
        <blockquote key={`quote-${currentBlockIndex++}`} className="markdown-blockquote">
          {quoteLines.map((ql, qIdx) => (
            <p key={`qp-${qIdx}`}>{renderInlineMarkdown(ql)}</p>
          ))}
        </blockquote>
      );
      continue;
    }

    // 5. Tables (| Header 1 | Header 2 |)
    if (trimmed.startsWith('|') && trimmed.endsWith('|') && lines[i + 1] && lines[i + 1].includes('---')) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        tableLines.push(lines[i].trim());
        i++;
      }

      if (tableLines.length >= 2) {
        const headerRow = tableLines[0].split('|').slice(1, -1).map((h) => h.trim());
        const bodyRows = tableLines.slice(2).map((r) =>
          r.split('|').slice(1, -1).map((c) => c.trim())
        );

        blocks.push(
          <div key={`table-${currentBlockIndex++}`} className="markdown-table-wrapper">
            <table className="markdown-table">
              <thead>
                <tr>
                  {headerRow.map((cell, cIdx) => (
                    <th key={`th-${cIdx}`}>{renderInlineMarkdown(cell)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {bodyRows.map((row, rIdx) => (
                  <tr key={`tr-${rIdx}`}>
                    {row.map((cell, cIdx) => (
                      <td key={`td-${cIdx}`}>{renderInlineMarkdown(cell)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        continue;
      }
    }

    // 6. Unordered List (* ..., - ...)
    if (/^[\*\-\+]\s+/.test(trimmed)) {
      const listItems: string[] = [];
      while (i < lines.length && /^[\*\-\+]\s+/.test(lines[i].trim())) {
        listItems.push(lines[i].trim().replace(/^[\*\-\+]\s+/, ''));
        i++;
      }
      blocks.push(
        <ul key={`ul-${currentBlockIndex++}`} className="markdown-ul">
          {listItems.map((item, itemIdx) => (
            <li key={`li-${itemIdx}`}>{renderInlineMarkdown(item)}</li>
          ))}
        </ul>
      );
      continue;
    }

    // 7. Ordered List (1. ..., 2. ...)
    if (/^\d+\.\s+/.test(trimmed)) {
      const listItems: string[] = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        listItems.push(lines[i].trim().replace(/^\d+\.\s+/, ''));
        i++;
      }
      blocks.push(
        <ol key={`ol-${currentBlockIndex++}`} className="markdown-ol">
          {listItems.map((item, itemIdx) => (
            <li key={`oli-${itemIdx}`}>{renderInlineMarkdown(item)}</li>
          ))}
        </ol>
      );
      continue;
    }

    // 8. Empty line
    if (!trimmed) {
      i++;
      continue;
    }

    // 9. Standard Paragraph (gather multi-line paragraphs until an empty line or special block)
    const paraLines: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !lines[i].trim().startsWith('#') &&
      !lines[i].trim().startsWith('```') &&
      !lines[i].trim().startsWith('>') &&
      !lines[i].trim().startsWith('|') &&
      !/^[\*\-\+]\s+/.test(lines[i].trim()) &&
      !/^\d+\.\s+/.test(lines[i].trim()) &&
      !/^(\-{3,}|\*{3,}|_{3,})$/.test(lines[i].trim())
    ) {
      paraLines.push(lines[i]);
      i++;
    }

    if (paraLines.length > 0) {
      blocks.push(
        <p key={`p-${currentBlockIndex++}`} className="markdown-p">
          {renderInlineMarkdown(paraLines.join('\n'))}
        </p>
      );
    }
  }

  return <div className="markdown-rendered-content">{blocks}</div>;
};
