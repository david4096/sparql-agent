# Prompt Engine Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        PROMPT ENGINE                             │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                     PromptEngine                         │  │
│  │  • Scenario Detection                                     │  │
│  │  • Context Building                                       │  │
│  │  • Example Management                                     │  │
│  │  • Template Selection                                     │  │
│  └──────────────┬───────────────────────────────────────────┘  │
│                 │                                                │
│                 ├──► Scenario Detection                          │
│                 │    (Keyword-based analysis)                   │
│                 │                                                │
│                 ├──► Context Building                            │
│                 │    ┌────────────────────────────────┐         │
│                 │    │    PromptContext               │         │
│                 │    │  • User Query                  │         │
│                 │    │  • Schema Info                 │         │
│                 │    │  • Ontology Info               │         │
│                 │    │  • Examples                    │         │
│                 │    │  • Prefixes                    │         │
│                 │    └────────────────────────────────┘         │
│                 │                                                │
│                 ├──► Template Rendering                          │
│                 │    ┌────────────────────────────────┐         │
│                 │    │   PromptTemplate (Jinja2)     │         │
│                 │    │  • Basic Template              │         │
│                 │    │  • Complex Join Template       │         │
│                 │    │  • Aggregation Template        │         │
│                 │    │  • Full-Text Template          │         │
│                 │    └────────────────────────────────┘         │
│                 │                                                │
│                 └──► Generated Prompt                            │
│                      (Ready for LLM)                             │
└─────────────────────────────────────────────────────────────────┘
```

## Component Interaction Flow

```
User Query
    │
    ├──► "Find all proteins from human"
    │
    ▼
┌─────────────────────┐
│ PromptEngine        │
│ .generate_prompt()  │
└──────────┬──────────┘
           │
           ├─── Step 1: Detect Scenario
           │    ├─► Analyze keywords
           │    ├─► "proteins" → BASIC
           │    └─► QueryScenario.BASIC
           │
           ├─── Step 2: Build Context
           │    ├─► Collect Schema Info
           │    │   ├─ Classes: up:Protein
           │    │   ├─ Properties: up:organism
           │    │   └─ Counts: 500,000 instances
           │    │
           │    ├─► Collect Ontology Info
           │    │   ├─ OWL Classes
           │    │   ├─ OWL Properties
           │    │   └─ Relationships
           │    │
           │    ├─► Build Prefixes
           │    │   ├─ up: http://purl.uniprot.org/core/
           │    │   ├─ rdfs: http://www.w3.org/.../rdf-schema#
           │    │   └─ rdf: http://www.w3.org/.../rdf-syntax-ns#
           │    │
           │    └─► Select Examples
           │        ├─ Filter by scenario: BASIC
           │        ├─ Filter by difficulty: ≤ 3
           │        └─ Limit: 5 examples
           │
           ├─── Step 3: Select Template
           │    ├─► Scenario: BASIC
           │    └─► Template: basic.j2
           │
           ├─── Step 4: Render Template
           │    ├─► Inject Context
           │    ├─► Format Ontology
           │    ├─► Format Schema
           │    ├─► Format Examples
           │    └─► Generate Prompt
           │
           ▼
    Generated Prompt
    (Complete, formatted, ready for LLM)
```

## Data Flow Diagram

```
Input Sources                Context Building              Output
─────────────               ──────────────────            ────────

User Query ─────────┐
                    │
Schema Info ────────┤
                    │       ┌──────────────┐
Ontology Info ──────┼──────►│ PromptContext │
                    │       └───────┬──────┘
Prefixes ───────────┤               │
                    │               │
Examples ───────────┘               │
                                    │
                                    ▼
                            ┌──────────────┐
                            │ Context      │
                            │ Processing   │
                            └───────┬──────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
            get_ontology_   get_schema_    get_prefix_
              context()      summary()    declarations()
                    │               │               │
                    └───────────────┼───────────────┘
                                    │
                                    ▼
                            ┌──────────────┐
                            │   Template   │
                            │   Renderer   │
                            │  (Jinja2)    │
                            └───────┬──────┘
                                    │
                                    ▼
                            Final Prompt Text
```

## Template Structure

```
┌─────────────────────────────────────────────────────────┐
│              SPARQL Prompt Template                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ## Question                                             │
│  {{ user_query }}                                        │
│                                                          │
│  ## Available Ontologies                                │
│  {{ ontology_context }}                                 │
│  ├─ Ontology Title                                      │
│  ├─ Description                                         │
│  ├─ Key Classes (Top 10)                                │
│  │  ├─ Label: Comment                                   │
│  │  └─ ...                                              │
│  └─ Key Properties (Top 10)                             │
│     ├─ Label: Comment                                   │
│     └─ ...                                              │
│                                                          │
│  ## Schema Information                                  │
│  {{ schema_summary }}                                   │
│  ├─ Most Common Classes                                 │
│  │  └─ URI (instance count)                            │
│  ├─ Most Common Properties                              │
│  │  └─ URI (usage count)                               │
│  └─ Property Domains/Ranges                             │
│     └─ Property → Domain, Range                         │
│                                                          │
│  ## Available Prefixes                                  │
│  {{ prefix_declarations }}                              │
│  ├─ PREFIX up: <http://...>                            │
│  ├─ PREFIX rdfs: <http://...>                          │
│  └─ ...                                                 │
│                                                          │
│  ## Examples (if enabled)                               │
│  {{ examples }}                                         │
│  ├─ Example 1:                                          │
│  │  ├─ Question: ...                                    │
│  │  └─ SPARQL: ...                                      │
│  └─ ...                                                 │
│                                                          │
│  ## Instructions                                        │
│  1. Generate valid SPARQL 1.1 query                     │
│  2. Use appropriate prefixes                            │
│  3. Leverage ontology classes/properties                │
│  4. Include comments                                    │
│  5. Use proper formatting                               │
│  6. Consider performance                                │
│                                                          │
│  ## Constraints (if any)                                │
│  {{ constraints }}                                      │
│  ├─ LIMIT: 100                                          │
│  ├─ timeout: 30 seconds                                 │
│  └─ ...                                                 │
│                                                          │
│  ## Generated SPARQL Query                              │
│  Please provide the SPARQL query below:                 │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Scenario Detection Logic

```
User Query Text
      │
      ▼
┌─────────────────────┐
│ Keyword Analysis    │
└─────────┬───────────┘
          │
          ├─► Contains: "count", "average", "sum", "how many", "total"
          │   └─► QueryScenario.AGGREGATION
          │
          ├─► Contains: "search", "find all", "contains", "matching"
          │   └─► QueryScenario.FULL_TEXT
          │
          ├─► Contains: "and", "associated with", "linked to", "related to"
          │   └─► QueryScenario.COMPLEX_JOIN
          │
          └─► Default
              └─► QueryScenario.BASIC
```

## Example Database Structure

```
┌──────────────────────────────────────────────────────────┐
│                    Examples Database                      │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  QueryScenario.BASIC                                      │
│  ├─ Example 1 [difficulty=1, tags=["protein", "basic"]]  │
│  │  ├─ Question: "Find all proteins from human"          │
│  │  ├─ SPARQL: "SELECT ?protein ..."                     │
│  │  └─ Explanation: "Basic query to find proteins..."    │
│  │                                                        │
│  └─ Example 2 [difficulty=1, tags=["disease", "list"]]   │
│     ├─ Question: "List all diseases"                     │
│     ├─ SPARQL: "SELECT ?disease ..."                     │
│     └─ Explanation: "Query to list diseases..."          │
│                                                           │
│  QueryScenario.COMPLEX_JOIN                               │
│  └─ Example 1 [difficulty=3, tags=["gene", "disease"]]   │
│     ├─ Question: "Find genes associated with diseases"   │
│     ├─ SPARQL: "SELECT ?gene ?disease ..."               │
│     └─ Explanation: "Join across genes and diseases..."  │
│                                                           │
│  QueryScenario.AGGREGATION                                │
│  ├─ Example 1 [difficulty=2, tags=["count", "group-by"]] │
│  └─ Example 2 [difficulty=3, tags=["average", "subquery"]]│
│                                                           │
│  QueryScenario.FULL_TEXT                                  │
│  └─ Example 1 [difficulty=2, tags=["search", "filter"]]  │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

## Context Processing Pipeline

```
1. Schema Info Input
   ┌─────────────────────┐
   │ SchemaInfo          │
   │ • classes           │
   │ • properties        │
   │ • namespaces        │
   │ • class_counts      │
   │ • property_counts   │
   └──────────┬──────────┘
              │
              ▼
   get_schema_summary()
              │
              ├─► Get top 10 classes by count
              ├─► Get top 10 properties by count
              ├─► Sample property domains/ranges
              └─► Format as text
              │
              ▼
   "Most Common Classes:
    - http://.../Protein (500,000 instances)
    - ...
    Most Common Properties:
    - http://.../organism (2,000 uses)
    - ..."

2. Ontology Info Input
   ┌─────────────────────┐
   │ OntologyInfo        │
   │ • uri               │
   │ • title             │
   │ • description       │
   │ • classes (Dict)    │
   │ • properties (Dict) │
   └──────────┬──────────┘
              │
              ▼
   get_ontology_context()
              │
              ├─► Format title & description
              ├─► Get top 10 classes
              │   └─► Format: label: comment
              ├─► Get top 10 properties
              │   └─► Format: label: comment
              └─► Combine into text
              │
              ▼
   "Ontology: UniProt Core
    Description: Ontology for proteins
    Key Classes:
    - Protein: A biological macromolecule
    - ..."

3. Prefix Building
   ┌─────────────────────┐
   │ • Schema namespaces │
   │ • Ontology namespaces│
   │ • Common prefixes   │
   └──────────┬──────────┘
              │
              ▼
   get_prefix_declarations()
              │
              ├─► Merge all namespaces
              ├─► Add rdf, rdfs, owl, xsd
              ├─► Sort alphabetically
              └─► Format as PREFIX statements
              │
              ▼
   "PREFIX rdf: <http://...>
    PREFIX rdfs: <http://...>
    PREFIX up: <http://...>"
```

## Integration Architecture

```
┌────────────────────────────────────────────────────────────┐
│                   External Systems                          │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────┐                   │
│  │   Schema     │      │   Ontology   │                   │
│  │  Inference   │      │   Parser     │                   │
│  │   Engine     │      │  (OWL/OLS)   │                   │
│  └───────┬──────┘      └───────┬──────┘                   │
│          │                     │                           │
│          │ SchemaInfo          │ OntologyInfo              │
│          │                     │                           │
│          └─────────┬───────────┘                           │
└────────────────────┼───────────────────────────────────────┘
                     │
                     ▼
         ┌─────────────────────┐
         │   Prompt Engine     │
         │  .generate_prompt() │
         └──────────┬──────────┘
                    │
                    │ Generated Prompt
                    │
                    ▼
         ┌─────────────────────┐
         │    LLM Provider     │
         │  (OpenAI/Anthropic) │
         └──────────┬──────────┘
                    │
                    │ SPARQL Query
                    │
                    ▼
         ┌─────────────────────┐
         │  SPARQL Validator   │
         │    (Optional)       │
         └──────────┬──────────┘
                    │
                    │ Validated Query
                    │
                    ▼
         ┌─────────────────────┐
         │  SPARQL Endpoint    │
         │   (Execution)       │
         └─────────────────────┘
```

## Performance Optimization Points

```
┌────────────────────────────────────────────┐
│         Performance Optimizations          │
├────────────────────────────────────────────┤
│                                             │
│  1. Template Caching                        │
│     ├─ Compile templates once              │
│     └─ Reuse compiled templates            │
│                                             │
│  2. Context Building                        │
│     ├─ Limit classes to top 10             │
│     ├─ Limit properties to top 10          │
│     └─ Sample property domains/ranges      │
│                                             │
│  3. Example Selection                       │
│     ├─ Early termination at limit          │
│     ├─ Filter by difficulty first          │
│     └─ O(n) complexity                     │
│                                             │
│  4. Scenario Detection                      │
│     ├─ Simple keyword matching             │
│     └─ O(1) lookup                         │
│                                             │
│  5. Prefix Management                       │
│     ├─ Deduplicate namespaces             │
│     └─ Sort once                           │
│                                             │
└────────────────────────────────────────────┘
```

## Extension Points

```
┌─────────────────────────────────────────────────────────┐
│                   Extension Points                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. Custom Scenarios                                     │
│     └─ Add new QueryScenario enum values                │
│                                                          │
│  2. Custom Templates                                     │
│     ├─ Create Jinja2 template strings                   │
│     └─ Add to template directory                        │
│                                                          │
│  3. Custom Examples                                      │
│     ├─ Define FewShotExample instances                  │
│     ├─ Load from JSON/YAML                              │
│     └─ Add via engine.add_example()                     │
│                                                          │
│  4. Context Enrichment                                   │
│     ├─ Extend PromptContext class                       │
│     └─ Add custom formatting methods                    │
│                                                          │
│  5. Template Variables                                   │
│     └─ Add custom variables to render()                 │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Error Handling

```
Error Scenarios
      │
      ├─► Missing Schema Info
      │   └─► Return "No schema information available"
      │
      ├─► Missing Ontology Info
      │   └─► Return "No ontology information available"
      │
      ├─► Empty Examples
      │   └─► Return "No examples available"
      │
      ├─► Template Not Found
      │   └─► Fall back to default template
      │
      └─► Invalid Scenario
          └─► Fall back to QueryScenario.BASIC
```

## Summary

The Prompt Engine provides a robust, extensible system for generating LLM prompts for SPARQL query generation. Key characteristics:

- **Modular Design**: Separate concerns (detection, context, templates)
- **Extensible**: Easy to add scenarios, templates, examples
- **Context-Aware**: Automatically includes relevant information
- **Performant**: Optimized for production use
- **Well-Tested**: Comprehensive test coverage
- **Documented**: Complete documentation and examples
