# BoundaryBench site design audit

This document records the reference study behind the public BoundaryBench site. The review was completed on September 3, 2026 using full-page captures and computed layout measurements from official OpenAI pages.

## Pages reviewed

* [OpenAI home](https://openai.com/)
* [OpenAI research overview](https://openai.com/research/)
* [OpenAI safety overview](https://openai.com/safety/)
* [OpenAI business](https://openai.com/business/)
* [OpenAI Codex](https://openai.com/codex/)
* [Introducing GPT-5.5](https://openai.com/index/introducing-gpt-5-5/)

The pages represent six different editorial jobs: a publication home, a research overview, a thematic explainer, a product narrative, a product launch, and a long-form technical article.

## Measured system

Measurements below were taken at a 1280 by 720 viewport.

| Element | OpenAI measurement | BoundaryBench translation |
| --- | --- | --- |
| Main page frame | 1216 pixels with 32 pixel side margins | 1216 pixel maximum frame with 32 pixel side margins |
| Reading column | 803 pixels | 803 pixel centered reading column |
| Body type | 17 pixels, 28 pixel line height, medium-tight tracking | 17 pixels, 1.647 line height, minus 0.01em tracking |
| Primary heading | 59.2 pixels, 59.9 pixel line height, weight 500 | 59.2 pixel maximum, 1.012 line height, weight 500 |
| Large section heading | 45.6 pixels, 52.8 pixel line height | 45.6 pixels for the final research callout |
| Editorial section heading | 29.1 pixels, 38.4 pixel line height | 29.1 pixels for research and method headings |
| Metadata and navigation | 14 pixels, weight 500 | 14 pixels, weight 500 |
| Hero media | 1009 by 568 pixels | 1009 pixel maximum width at 16 by 9 |
| Major section interval | About 120 pixels | 120 pixel desktop cadence |

OpenAI uses its own OpenAI Sans family. BoundaryBench does not redistribute that proprietary font. The site uses the native system sans stack with the same measured size, weight, line height, and tracking relationships.

## Page structure

### Navigation

The primary OpenAI header is a single horizontal line of text. The wordmark has the strongest weight. Navigation is 14 pixels and visually quiet. The final action sits at the far edge. The header does not use a bottom rule, oversized logo treatment, or secondary brand sentence.

BoundaryBench follows the same hierarchy with a text wordmark, four section links, and one GitHub destination. The former circular mark, bordered navigation, and filled call-to-action were removed.

### Opening section

The research and safety pages center a short category label, a 59 pixel headline, a short paragraph, and a small set of actions inside an 803 pixel column. The hero image begins 64 pixels below the actions and widens to 1009 pixels. The opening makes one claim and then lets the media carry the visual weight.

BoundaryBench now opens with one research question, one sentence of scope, two underlined text links, and the original boundary field image. Overlay labels, image metadata, decorative badges, and scroll instructions were removed.

### Editorial transition

After the hero media, OpenAI leaves roughly 120 pixels before the next label and statement. The next statement is smaller than the hero and remains centered in the same 803 pixel reading column. This creates progression without introducing a new visual component.

BoundaryBench uses the same transition for its central question: can an agent distinguish useful context from permission to act?

### Compositional rhythm

The Codex page changes composition as the reader moves down the page. Its opening is centered, while later sections alternate between text and evidence. Large media blocks provide tonal variation without changing the underlying type system.

BoundaryBench keeps the centered opening, then shifts to left-aligned statements, split method and record sections, and a wide evidence comparison. This removes the repeated centered stacks from the earlier draft. Blue light is limited to the hero atmosphere, study diagrams, and closing panel so the visual identity remains tied to the boundary field artwork.

### Research groups

The OpenAI research page introduces each domain with a 29 pixel title and a single paragraph, then presents equally sized media blocks in a strict grid. Titles and metadata sit below the media rather than inside it. The layout repeats while the content changes.

BoundaryBench uses three equal research figures for provenance, position, and repetition. Each figure is a functional diagram of the study factor, followed by a title and one line describing its levels. Gradient cards, oversized lettering inside cards, status dots, and repeated repository links were removed.

### Technical evidence

The GPT-5.5 article uses a narrow reading column for prose and full-width space for charts and tables. Data is separated by thin rules. Tables do not sit inside ornamental cards. Captions are small, direct, and close to the evidence they describe.

BoundaryBench uses a ruled study-design table for scenarios, factorial conditions, controlled cases, and preregistered cases. The evidence section uses three columns with shared rules rather than individual cards. No illustrative performance values appear on the site.

### Public record

OpenAI’s system-card list is a sequence of compact rows separated by one-pixel rules. Each row keeps the document title on the left and a simple destination on the right. The structure scales well because it is repetitive without being decorative.

BoundaryBench uses the same row grammar for the research record, preregistration, conformance result, and citation. Each row states the artifact, its purpose, and its file type.

### Closing panel

OpenAI frequently closes a page with a large dark-gray block containing one centered statement and one action. This is the strongest tonal change outside the page media.

BoundaryBench closes with a single dark-gray panel that points to the complete GitHub record. It has no colored background, symbol, slogan stack, or secondary action.

### Footer

The OpenAI footer returns to a broad multi-column index. Headings are muted. Links are compact and evenly spaced. The legal row sits below the directory rather than competing with it.

BoundaryBench uses four columns for Research, Method, Project, and Use, followed by a quiet three-part identity row.

## Content rules

1. One idea per section.
2. One explanatory sentence when a heading is not sufficient.
3. Research terms replace marketing language.
4. Links name the destination directly.
5. No arrow characters or decorative link symbols.
6. No fabricated metrics, example scores, or visualized outcomes.
7. The repository remains the canonical record.

## Visual rules

1. Black, white, and neutral gray carry the interface.
2. Color appears in the research image and measured diagrams.
3. Display type uses medium weight and restrained tracking.
4. Major page intervals use a 120 pixel desktop cadence.
5. Media aligns to the 1216 pixel frame or the 1009 pixel hero width.
6. Long-form text and tables align to the 803 pixel reading column.
7. Rules define structure before backgrounds, borders, or shadows.
