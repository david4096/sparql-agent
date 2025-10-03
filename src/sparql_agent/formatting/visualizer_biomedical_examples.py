"""
Biomedical visualization examples for SPARQL results.

This module demonstrates how to use the visualization tools for common
biomedical data patterns including gene networks, protein interactions,
disease associations, and clinical trial data.
"""

from sparql_agent.core.types import QueryResult, QueryStatus
from sparql_agent.formatting.visualizer import (
    GraphVisualizer,
    ChartGenerator,
    VisualizationConfig,
    NetworkGraphConfig,
    ChartConfig,
    LayoutAlgorithm,
    ColorSchemes,
    TimeSeriesDetector,
    auto_visualize,
)


def example_gene_interaction_network():
    """
    Example 1: Gene-gene interaction network.

    Visualizes protein-protein interactions or gene regulatory networks
    commonly found in biological databases.
    """
    print("=" * 80)
    print("Example 1: Gene Interaction Network")
    print("=" * 80)

    # Sample gene interaction data
    result = QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["gene1", "interaction_type", "gene2"],
        bindings=[
            {
                "gene1": {"type": "uri", "value": "http://bio2rdf.org/hgnc:TP53"},
                "interaction_type": {"type": "uri", "value": "http://purl.org/obo/ro/activates"},
                "gene2": {"type": "uri", "value": "http://bio2rdf.org/hgnc:MDM2"},
            },
            {
                "gene1": {"type": "uri", "value": "http://bio2rdf.org/hgnc:TP53"},
                "interaction_type": {"type": "uri", "value": "http://purl.org/obo/ro/regulates"},
                "gene2": {"type": "uri", "value": "http://bio2rdf.org/hgnc:BAX"},
            },
            {
                "gene1": {"type": "uri", "value": "http://bio2rdf.org/hgnc:MDM2"},
                "interaction_type": {"type": "uri", "value": "http://purl.org/obo/ro/inhibits"},
                "gene2": {"type": "uri", "value": "http://bio2rdf.org/hgnc:TP53"},
            },
            {
                "gene1": {"type": "uri", "value": "http://bio2rdf.org/hgnc:BAX"},
                "interaction_type": {"type": "uri", "value": "http://purl.org/obo/ro/activates"},
                "gene2": {"type": "uri", "value": "http://bio2rdf.org/hgnc:CASP3"},
            },
            {
                "gene1": {"type": "uri", "value": "http://bio2rdf.org/hgnc:TP53"},
                "interaction_type": {"type": "uri", "value": "http://purl.org/obo/ro/regulates"},
                "gene2": {"type": "uri", "value": "http://bio2rdf.org/hgnc:CDKN1A"},
            },
        ],
        row_count=5,
    )

    try:
        # Configure with biomedical color scheme
        viz_config = VisualizationConfig(
            width=1400,
            height=900,
            title="Gene Interaction Network (TP53 Pathway)",
            show_legend=True,
            color_scheme="Pathways",
            background_color="#fafafa",
            interactive=True,
        )

        graph_config = NetworkGraphConfig(
            layout=LayoutAlgorithm.KAMADA_KAWAI,
            node_size=50,
            node_color="#e74c3c",
            edge_width=2.5,
            edge_color="#95a5a6",
            show_node_labels=True,
            show_edge_labels=True,
            curved_edges=True,
            max_nodes=200,
        )

        visualizer = GraphVisualizer(
            backend="plotly",
            config=viz_config,
            graph_config=graph_config
        )

        fig = visualizer.create_network_graph(
            result,
            subject_var="gene1",
            predicate_var="interaction_type",
            object_var="gene2"
        )

        visualizer.save_html(fig, "/tmp/gene_network.html")
        print("Created gene interaction network: /tmp/gene_network.html")

        # Also export for D3.js
        import json
        d3_data = visualizer.export_d3_json(
            result,
            subject_var="gene1",
            predicate_var="interaction_type",
            object_var="gene2"
        )
        with open("/tmp/gene_network_d3.json", "w") as f:
            json.dump(d3_data, f, indent=2)
        print("Exported D3.js data: /tmp/gene_network_d3.json")

    except ImportError as e:
        print(f"Skipping: {e}")


def example_disease_prevalence():
    """
    Example 2: Disease prevalence by category.

    Bar chart showing disease counts or prevalence across different
    categories or populations.
    """
    print("\n" + "=" * 80)
    print("Example 2: Disease Prevalence by Category")
    print("=" * 80)

    result = QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["disease_category", "patient_count"],
        bindings=[
            {"disease_category": {"type": "literal", "value": "Cardiovascular"}, "patient_count": {"type": "literal", "value": "15420"}},
            {"disease_category": {"type": "literal", "value": "Cancer"}, "patient_count": {"type": "literal", "value": "12850"}},
            {"disease_category": {"type": "literal", "value": "Diabetes"}, "patient_count": {"type": "literal", "value": "9340"}},
            {"disease_category": {"type": "literal", "value": "Respiratory"}, "patient_count": {"type": "literal", "value": "8760"}},
            {"disease_category": {"type": "literal", "value": "Neurological"}, "patient_count": {"type": "literal", "value": "6520"}},
            {"disease_category": {"type": "literal", "value": "Infectious"}, "patient_count": {"type": "literal", "value": "5890"}},
        ],
        row_count=6,
    )

    try:
        viz_config = VisualizationConfig(
            title="Disease Prevalence by Category",
            width=1000,
            height=600,
            color_scheme="Viridis",
        )

        chart_config = ChartConfig(
            x_axis_label="Disease Category",
            y_axis_label="Number of Patients",
            show_values=True,
            show_grid=True,
        )

        generator = ChartGenerator(
            backend="plotly",
            config=viz_config,
            chart_config=chart_config
        )

        fig = generator.create_bar_chart(
            result,
            x_var="disease_category",
            y_var="patient_count"
        )

        generator.save(fig, "/tmp/disease_prevalence.html")
        print("Created disease prevalence chart: /tmp/disease_prevalence.html")

    except ImportError as e:
        print(f"Skipping: {e}")


def example_clinical_trial_timeline():
    """
    Example 3: Clinical trial enrollment over time.

    Line chart showing temporal trends in clinical research,
    such as trial enrollment, publication counts, or disease incidence.
    """
    print("\n" + "=" * 80)
    print("Example 3: Clinical Trial Enrollment Timeline")
    print("=" * 80)

    result = QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["year", "trials_enrolled"],
        bindings=[
            {"year": {"type": "literal", "value": "2018"}, "trials_enrolled": {"type": "literal", "value": "1850"}},
            {"year": {"type": "literal", "value": "2019"}, "trials_enrolled": {"type": "literal", "value": "2120"}},
            {"year": {"type": "literal", "value": "2020"}, "trials_enrolled": {"type": "literal", "value": "1680"}},
            {"year": {"type": "literal", "value": "2021"}, "trials_enrolled": {"type": "literal", "value": "2450"}},
            {"year": {"type": "literal", "value": "2022"}, "trials_enrolled": {"type": "literal", "value": "2890"}},
            {"year": {"type": "literal", "value": "2023"}, "trials_enrolled": {"type": "literal", "value": "3120"}},
        ],
        row_count=6,
    )

    try:
        # Verify time series detection
        is_time_series = TimeSeriesDetector.is_time_series(result)
        print(f"Time series detected: {is_time_series}")

        viz_config = VisualizationConfig(
            title="Clinical Trial Enrollment Over Time",
            width=1100,
            height=650,
            color_scheme="Blues",
        )

        chart_config = ChartConfig(
            x_axis_label="Year",
            y_axis_label="Number of Trials",
            show_grid=True,
            line_width=3.0,
            marker_size=12,
        )

        generator = ChartGenerator(
            backend="plotly",
            config=viz_config,
            chart_config=chart_config
        )

        fig = generator.create_line_chart(
            result,
            x_var="year",
            y_var="trials_enrolled"
        )

        generator.save(fig, "/tmp/clinical_trials_timeline.html")
        print("Created clinical trials timeline: /tmp/clinical_trials_timeline.html")

    except ImportError as e:
        print(f"Skipping: {e}")


def example_gene_expression_heatmap():
    """
    Example 4: Gene expression heatmap.

    Heatmap showing gene expression levels across different samples
    or conditions, a common visualization in genomics.
    """
    print("\n" + "=" * 80)
    print("Example 4: Gene Expression Heatmap")
    print("=" * 80)

    result = QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["gene", "sample", "expression_level"],
        bindings=[
            {"gene": {"type": "literal", "value": "BRCA1"}, "sample": {"type": "literal", "value": "Normal"}, "expression_level": {"type": "literal", "value": "5.2"}},
            {"gene": {"type": "literal", "value": "BRCA1"}, "sample": {"type": "literal", "value": "Tumor"}, "expression_level": {"type": "literal", "value": "12.8"}},
            {"gene": {"type": "literal", "value": "BRCA1"}, "sample": {"type": "literal", "value": "Metastasis"}, "expression_level": {"type": "literal", "value": "15.4"}},
            {"gene": {"type": "literal", "value": "TP53"}, "sample": {"type": "literal", "value": "Normal"}, "expression_level": {"type": "literal", "value": "7.1"}},
            {"gene": {"type": "literal", "value": "TP53"}, "sample": {"type": "literal", "value": "Tumor"}, "expression_level": {"type": "literal", "value": "3.2"}},
            {"gene": {"type": "literal", "value": "TP53"}, "sample": {"type": "literal", "value": "Metastasis"}, "expression_level": {"type": "literal", "value": "2.1"}},
            {"gene": {"type": "literal", "value": "MYC"}, "sample": {"type": "literal", "value": "Normal"}, "expression_level": {"type": "literal", "value": "4.5"}},
            {"gene": {"type": "literal", "value": "MYC"}, "sample": {"type": "literal", "value": "Tumor"}, "expression_level": {"type": "literal", "value": "18.6"}},
            {"gene": {"type": "literal", "value": "MYC"}, "sample": {"type": "literal", "value": "Metastasis"}, "expression_level": {"type": "literal", "value": "22.3"}},
        ],
        row_count=9,
    )

    try:
        viz_config = VisualizationConfig(
            title="Gene Expression Levels Across Sample Types",
            width=900,
            height=700,
            color_scheme="RdYlBu",
        )

        chart_config = ChartConfig(
            show_values=True,
        )

        generator = ChartGenerator(
            backend="plotly",
            config=viz_config,
            chart_config=chart_config
        )

        fig = generator.create_heatmap(
            result,
            row_var="gene",
            col_var="sample",
            value_var="expression_level"
        )

        generator.save(fig, "/tmp/gene_expression_heatmap.html")
        print("Created gene expression heatmap: /tmp/gene_expression_heatmap.html")

    except ImportError as e:
        print(f"Skipping: {e}")


def example_drug_efficacy_scatter():
    """
    Example 5: Drug efficacy correlation.

    Scatter plot showing relationship between drug dosage and
    therapeutic response or between two efficacy metrics.
    """
    print("\n" + "=" * 80)
    print("Example 5: Drug Efficacy Correlation")
    print("=" * 80)

    result = QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["dosage_mg", "response_rate"],
        bindings=[
            {"dosage_mg": {"type": "literal", "value": "10"}, "response_rate": {"type": "literal", "value": "15"}},
            {"dosage_mg": {"type": "literal", "value": "25"}, "response_rate": {"type": "literal", "value": "28"}},
            {"dosage_mg": {"type": "literal", "value": "50"}, "response_rate": {"type": "literal", "value": "42"}},
            {"dosage_mg": {"type": "literal", "value": "100"}, "response_rate": {"type": "literal", "value": "68"}},
            {"dosage_mg": {"type": "literal", "value": "200"}, "response_rate": {"type": "literal", "value": "82"}},
            {"dosage_mg": {"type": "literal", "value": "400"}, "response_rate": {"type": "literal", "value": "85"}},
            {"dosage_mg": {"type": "literal", "value": "800"}, "response_rate": {"type": "literal", "value": "86"}},
        ],
        row_count=7,
    )

    try:
        viz_config = VisualizationConfig(
            title="Drug Dosage vs Response Rate",
            width=900,
            height=700,
            color_scheme="Plasma",
        )

        chart_config = ChartConfig(
            x_axis_label="Dosage (mg)",
            y_axis_label="Response Rate (%)",
            show_grid=True,
            marker_size=15,
        )

        generator = ChartGenerator(
            backend="plotly",
            config=viz_config,
            chart_config=chart_config
        )

        fig = generator.create_scatter_plot(
            result,
            x_var="dosage_mg",
            y_var="response_rate"
        )

        generator.save(fig, "/tmp/drug_efficacy_scatter.html")
        print("Created drug efficacy scatter plot: /tmp/drug_efficacy_scatter.html")

    except ImportError as e:
        print(f"Skipping: {e}")


def example_protein_pathway_network():
    """
    Example 6: Protein pathway network with colorblind-safe colors.

    Network visualization of protein pathways using colorblind-friendly
    color schemes for accessibility.
    """
    print("\n" + "=" * 80)
    print("Example 6: Protein Pathway Network (Colorblind-Safe)")
    print("=" * 80)

    result = QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["protein_a", "pathway", "protein_b"],
        bindings=[
            {
                "protein_a": {"type": "uri", "value": "http://identifiers.org/uniprot/P04637"},
                "pathway": {"type": "literal", "value": "Apoptosis"},
                "protein_b": {"type": "uri", "value": "http://identifiers.org/uniprot/Q00987"},
            },
            {
                "protein_a": {"type": "uri", "value": "http://identifiers.org/uniprot/P04637"},
                "pathway": {"type": "literal", "value": "Cell Cycle"},
                "protein_b": {"type": "uri", "value": "http://identifiers.org/uniprot/P38936"},
            },
            {
                "protein_a": {"type": "uri", "value": "http://identifiers.org/uniprot/Q00987"},
                "pathway": {"type": "literal", "value": "Apoptosis"},
                "protein_b": {"type": "uri", "value": "http://identifiers.org/uniprot/P42574"},
            },
            {
                "protein_a": {"type": "uri", "value": "http://identifiers.org/uniprot/P38936"},
                "pathway": {"type": "literal", "value": "Cell Cycle"},
                "protein_b": {"type": "uri", "value": "http://identifiers.org/uniprot/P06493"},
            },
        ],
        row_count=4,
    )

    try:
        # Use colorblind-safe scheme
        colorblind_colors = ColorSchemes.get_scheme("colorblind_safe")
        print(f"Using colorblind-safe scheme: {colorblind_colors[:3]}...")
        print(f"Is colorblind safe: {ColorSchemes.is_colorblind_safe('colorblind_safe')}")

        viz_config = VisualizationConfig(
            width=1200,
            height=800,
            title="Protein Pathway Network (Colorblind-Friendly)",
            color_scheme="Deuteranopia",
            background_color="white",
        )

        graph_config = NetworkGraphConfig(
            layout=LayoutAlgorithm.CIRCULAR,
            node_size=45,
            node_color="#0173B2",
            edge_width=3.0,
            edge_color="#949494",
            show_node_labels=True,
        )

        visualizer = GraphVisualizer(
            backend="plotly",
            config=viz_config,
            graph_config=graph_config
        )

        fig = visualizer.create_network_graph(result)

        visualizer.save_html(fig, "/tmp/protein_pathway_colorblind.html")
        print("Created colorblind-safe pathway network: /tmp/protein_pathway_colorblind.html")

    except ImportError as e:
        print(f"Skipping: {e}")


def example_auto_visualization_biomedical():
    """
    Example 7: Automatic visualization selection for biomedical data.

    Demonstrates smart visualization selection that automatically
    chooses the best visualization type based on data patterns.
    """
    print("\n" + "=" * 80)
    print("Example 7: Automatic Visualization Selection")
    print("=" * 80)

    # Example 1: Variant frequency data (should choose bar chart)
    variant_data = QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["variant", "frequency"],
        bindings=[
            {"variant": {"type": "literal", "value": "rs12345"}, "frequency": {"type": "literal", "value": "0.42"}},
            {"variant": {"type": "literal", "value": "rs67890"}, "frequency": {"type": "literal", "value": "0.35"}},
            {"variant": {"type": "literal", "value": "rs11223"}, "frequency": {"type": "literal", "value": "0.28"}},
        ],
        row_count=3,
    )

    # Example 2: Protein-protein interaction (should choose network graph)
    ppi_data = QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["protein1", "protein2"],
        bindings=[
            {
                "protein1": {"type": "uri", "value": "http://string-db.org/protein/9606.ENSP00000269305"},
                "protein2": {"type": "uri", "value": "http://string-db.org/protein/9606.ENSP00000344818"},
            },
        ],
        row_count=1,
    )

    try:
        # Auto-visualize variant data
        print("\nVariant frequency data:")
        fig1 = auto_visualize(variant_data)
        print("  -> Created automatic visualization")

        # Auto-visualize PPI data
        print("\nProtein-protein interaction data:")
        fig2 = auto_visualize(ppi_data)
        print("  -> Created automatic visualization")

    except ImportError as e:
        print(f"Skipping: {e}")


def main():
    """Run all biomedical examples."""
    print("\n" + "=" * 80)
    print("SPARQL Agent Biomedical Visualization Examples")
    print("=" * 80)

    examples = [
        example_gene_interaction_network,
        example_disease_prevalence,
        example_clinical_trial_timeline,
        example_gene_expression_heatmap,
        example_drug_efficacy_scatter,
        example_protein_pathway_network,
        example_auto_visualization_biomedical,
    ]

    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"Error in {example_func.__name__}: {e}")

    print("\n" + "=" * 80)
    print("All biomedical examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
