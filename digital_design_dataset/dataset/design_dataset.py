import json
import operator
import os
import re
import shutil
from pathlib import Path
from typing import Any, Optional

import networkx as nx
import tqdm
from github import Auth, Github
from joblib import Parallel, delayed

from digital_design_dataset.flows.design_hierarchy import extract_design_hierarchy
from digital_design_dataset.flows.verilog_ast import verilog_ast
from digital_design_dataset.flows.yosys_aig import yosys_aig

VERILOG_SOURCE_EXTENSIONS = [".v", ".sv", ".svh", ".vh", ".h", ".inc"]
VERILOG_SOURCE_EXTENSIONS_SET = set(VERILOG_SOURCE_EXTENSIONS) | {
    ext.upper() for ext in VERILOG_SOURCE_EXTENSIONS
}

HARDWARE_DATA_TEXT_EXTENSIONS = [".coe", ".mif", ".mem"]
HARDWARE_DATA_TEXT_EXTENSIONS_SET = set(HARDWARE_DATA_TEXT_EXTENSIONS) | {
    ext.upper() for ext in HARDWARE_DATA_TEXT_EXTENSIONS
}

SOURCE_FILES_EXTENSIONS_SET = (
    VERILOG_SOURCE_EXTENSIONS_SET | HARDWARE_DATA_TEXT_EXTENSIONS_SET
)

# === General Notes and TODOs ===
# - Refactor this to multiple files, one for metaobjects,
#   one for dataset retrievers, one for flows, ...
#
# - Make sure type hints are comprehensive
#
# - Use pydantic to enfore a dataset stucture and metadata structure,
#   this reuires non-trivial changes but is worth it


class DirectoryNotEmptyError(Exception): ...


def make_dir_if_not_empty(path: Path) -> None:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    elif len(os.listdir(path)) > 0:
        raise DirectoryNotEmptyError(
            "Directory is not empty. Support for partially constructed "
            "datasets is not implemented yet.",
        )


class DesignDataset:
    def __init__(
        self,
        dataset_dir: Path,
        overwrite: bool = False,
        gh_token: str | None = None,
    ) -> None:
        self.dataset_dir = dataset_dir

        if overwrite and self.dataset_dir.exists():
            shutil.rmtree(self.dataset_dir)

        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        self.designs_dir.mkdir(parents=True, exist_ok=True)

        self.gh_token = gh_token
        if self.gh_token is not None:
            self.gh_api = Github(auth=Auth.Token(self.gh_token))
        else:
            self.gh_api = Github()

    @property
    def root_dir(self) -> Path:
        return self.dataset_dir

    @property
    def designs_dir(self) -> Path:
        return self.dataset_dir / "designs"

    @property
    def index_path(self) -> Path:
        return self.dataset_dir / "index.json"

    @property
    def does_index_exist(self) -> bool:
        return self.index_path.exists()

    @property
    def index(self) -> list[dict]:
        designs = []
        for design_dir in self.designs_dir.iterdir():
            design_json_fp = design_dir / "design.json"
            with design_json_fp.open() as f:
                design = json.load(f)
            designs.append(design)
        designs = sorted(designs, key=operator.itemgetter("design_name"))
        return designs

    # TODO: make index as a generator
    @property
    def index_generator(self) -> None:
        raise NotImplementedError

    def get_design_metadata_by_design_name(self, design_name: str) -> dict | None:
        """Retrieves the metadata of a design based on its design name.

        Args:
        ----
            design_name (str): The name of the design.

        Returns:
        -------
            dict | None: The metadata of the design if found, None otherwise.

        """
        metadata = None
        for design in self.index:
            if design["design_name"] == design_name:
                metadata = design
                break
        return metadata

    def get_design_metadata_by_design_name_regex(
        self,
        design_name_regex_pattern: str,
    ) -> list[dict]:
        """Retrieves the design metadata for designs whose names match the given
        regular expression pattern.

        Args:
        ----
            design_name_regex_pattern (str): The regular expression pattern to
            match against design names.

        Returns:
        -------
            list[dict]: A list of dictionaries containing the metadata of
            designs that match the pattern.

        """
        metadata = [
            design
            for design in self.index
            if re.match(design_name_regex_pattern, design["design_name"])
        ]
        return metadata

    def get_design_metadata_by_dataset_name(self, dataset_name: str) -> list[dict]:
        """Retrieves all design metadata for designs in a given dataset,
        identified by the dataset name.

        Args:
        ----
            dataset_name (str): The name of the dataset.

        Returns:
        -------
            list[dict]: A list of design metadata dictionaries matching the
            given dataset name.

        """
        metadata = [
            design for design in self.index if design["dataset_name"] == dataset_name
        ]
        return metadata

    def get_design_source_files(self, design_name: str) -> list[Path]:
        """Retrieves the source files for a given design name.

        Args:
        ----
            design_name (str): The name of the design.

        Returns:
        -------
            list[Path]: A list of Path objects representing the source files.

        """
        design_sources_dir = self.designs_dir / design_name / "sources"
        source_files = list(design_sources_dir.iterdir())
        return source_files


class Flow:
    flow_name: str
    flow_type: str  # TODO: Chnage to be more like tags, like a list[str]

    def __init__(self, design_dataset: DesignDataset) -> None:
        self.design_dataset = design_dataset

    def build_flow(self, overwrite: bool = False) -> None:
        raise NotImplementedError


class LineCountFlow(Flow):
    flow_name = "line_count"
    flow_type = "text"

    def build_flow_single(
        self,
        design: dict[str, Any],
        overwrite: bool = False,
    ) -> None:
        # count number of lines in a design
        design_dir = self.design_dataset.designs_dir / design["design_name"]
        sources_dir = design_dir / "sources"
        sources_fps = [f for f in sources_dir.iterdir() if f.is_file()]

        lines = 0
        for source_fp in sources_fps:
            with source_fp.open() as f:
                lines += len(f.readlines())

        flow_dir = design_dir / "flows" / self.flow_name
        if flow_dir.exists():
            shutil.rmtree(flow_dir)
        flow_dir.mkdir(parents=True, exist_ok=True)

        flow_metadata = {
            "flow_name": self.flow_name,
            "flow_type": self.flow_type,
            "num_lines": lines,
        }

        num_lines = flow_dir / "num_lines.txt"
        num_lines.write_text(str(lines))

        flow_metadata_fp = flow_dir / "flow.json"
        flow_metadata_fp.write_text(json.dumps(flow_metadata, indent=4))

    def build_flow(self, overwrite: bool = False, n_jobs: int = 1) -> None:
        designs = self.design_dataset.index
        Parallel(n_jobs=n_jobs)(
            delayed(self.build_flow_single)(design, overwrite=overwrite)
            for design in designs
        )


class ModuleInfoFlow(Flow):
    flow_name = "module_count"
    flow_type = "text"

    def __init__(self, design_dataset: DesignDataset, yosys_bin: str = "yosys") -> None:
        super().__init__(design_dataset)
        self.yosys_bin = yosys_bin

    def build_flow_single(
        self,
        design: dict[str, Any],
        overwrite: bool = False,
    ) -> None:
        # count number of modules in a design
        design_dir = self.design_dataset.designs_dir / design["design_name"]
        sources_dir = design_dir / "sources"
        sources_fps = [f for f in sources_dir.iterdir() if f.is_file()]

        verilog_sources_fps = [
            f for f in sources_fps if f.suffix in VERILOG_SOURCE_EXTENSIONS_SET
        ]

        modules = extract_design_hierarchy(verilog_sources_fps)
        num_modules = len(modules)

        flow_dir = design_dir / "flows" / self.flow_name
        if flow_dir.exists():
            shutil.rmtree(flow_dir)
        flow_dir.mkdir(parents=True, exist_ok=True)

        flow_metadata = {
            "flow_name": self.flow_name,
            "flow_type": self.flow_type,
            "modules": modules,
            "num_modules": num_modules,
        }

        num_modules_fp = flow_dir / "num_modules.txt"
        num_modules_fp.write_text(str(num_modules))

        modules_fp = flow_dir / "modules.txt"
        modules_fp.write_text("\n".join(modules))

        flow_metadata_fp = flow_dir / "flow.json"
        flow_metadata_fp.write_text(json.dumps(flow_metadata, indent=4))

    def build_flow(self, overwrite: bool = False, n_jobs: int = 1) -> None:
        designs = self.design_dataset.index
        Parallel(n_jobs=n_jobs)(
            delayed(self.build_flow_single)(design, overwrite=overwrite)
            for design in tqdm.tqdm(designs)
        )
        self.build_flow_single(designs[0], overwrite=overwrite)


class VeribleASTFlow(Flow):
    flow_name = "yosys_ast"
    flow_type = "graph"

    def __init__(
        self,
        design_dataset: DesignDataset,
        verible_verilog_syntax_bin: str = "verible-verilog-syntax",
    ) -> None:
        super().__init__(design_dataset)
        self.verible_verilog_syntax_bin = verible_verilog_syntax_bin

    def build_flow_single(
        self,
        design: dict[str, Any],
        overwrite: bool = False,
    ) -> None:
        design_dir = self.design_dataset.designs_dir / design["design_name"]
        sources_dir = design_dir / "sources"
        sources_fps = [f for f in sources_dir.iterdir() if f.is_file()]

        # TODO: add overwrite functionality
        flow_dir = design_dir / "flows" / self.flow_name
        if flow_dir.exists():
            shutil.rmtree(flow_dir)
        flow_dir.mkdir(parents=True, exist_ok=True)

        design_metadata_fp = design_dir / "design.json"
        with design_metadata_fp.open() as f:
            design_metadata = json.load(f)

        if "flows" not in design_metadata:
            design_metadata["flows"] = {}

        flow_metadata = {}
        flow_metadata["flow_name"] = self.flow_name
        flow_metadata["flow_type"] = self.flow_type
        design_metadata["flows"][self.flow_name] = flow_metadata

        design_metadata_fp.write_text(json.dumps(design_metadata, indent=4))

        for source_fp in sources_fps:
            if source_fp.suffix not in VERILOG_SOURCE_EXTENSIONS_SET:
                continue
            g_ast = verilog_ast(
                source_fp,
                verible_verilog_syntax_bin=self.verible_verilog_syntax_bin,
            )
            if g_ast is None:
                raise ValueError(f"FAILED to parse {source_fp}")

            g_ast_json = nx.node_link_data(g_ast)
            g_ast_fp = flow_dir / (source_fp.stem + ".ast.json")
            g_ast_fp.write_text(json.dumps(g_ast_json, indent=4))

    def build_flow(self, overwrite: bool = False, n_jobs: int = 1) -> None:
        designs = self.design_dataset.index
        Parallel(n_jobs=n_jobs)(
            delayed(self.build_flow_single)(design, overwrite=overwrite)
            for design in designs
        )


class YosysAIGFlow(Flow):
    flow_name = "yosys_aig"
    flow_type = "graph"

    def __init__(self, design_dataset: DesignDataset, yosys_bin: str = "yosys") -> None:
        super().__init__(design_dataset)
        self.yosys_bin = yosys_bin

    def build_flow_single(
        self,
        design: dict[str, Any],
        overwrite: bool = False,
    ) -> None:
        design_dir = self.design_dataset.designs_dir / design["design_name"]
        sources_dir = design_dir / "sources"
        sources_fps = [f for f in sources_dir.iterdir() if f.is_file()]
        sources_fps = [
            f for f in sources_fps if f.suffix in VERILOG_SOURCE_EXTENSIONS_SET
        ]

        # TODO: add overwrite functionality
        flow_dir = design_dir / "flows" / self.flow_name
        if flow_dir.exists():
            shutil.rmtree(flow_dir)
        flow_dir.mkdir(parents=True, exist_ok=True)

        design_metadata_fp = design_dir / "design.json"
        with design_metadata_fp.open() as f:
            design_metadata = json.load(f)

        if "flows" not in design_metadata:
            design_metadata["flows"] = {}

        flow_metadata = {}
        flow_metadata["flow_name"] = self.flow_name
        flow_metadata["flow_type"] = self.flow_type
        design_metadata["flows"][self.flow_name] = flow_metadata

        design_metadata_fp.write_text(json.dumps(design_metadata, indent=4))

        aig_graph, json_data, stat_txt, stat_json = yosys_aig(
            sources_fps,
            yosys_bin=self.yosys_bin,
        )
        aig_graph_json = nx.node_link_data(aig_graph)
        aig_graph_fp = flow_dir / "aig_graph.json"
        aig_graph_fp.write_text(json.dumps(aig_graph_json, indent=4))

        aig_yosys_json_fp = flow_dir / "aig_yosys.json"
        aig_yosys_json_fp.write_text(json.dumps(json_data, indent=4))

        stat_txt_fp = flow_dir / "stat.txt"
        stat_txt_fp.write_text(stat_txt)

        stat_json_fp = flow_dir / "stat.json"
        stat_json_fp.write_text(json.dumps(stat_json, indent=4))

    def build_flow(self, overwrite: bool = False, n_jobs: int = 1) -> None:
        designs = self.design_dataset.index
        Parallel(n_jobs=n_jobs, backend="loky")(
            delayed(self.build_flow_single)(design, overwrite=overwrite)
            for design in tqdm.tqdm(designs)
        )


class YosysXilinxSynthFlow(Flow):
    flow_name = "yosys_xilinx_synth"
    flow_type = "graph"

    def __init__(self, design_dataset: DesignDataset, yosys_bin: str = "yosys") -> None:
        super().__init__(design_dataset)
        self.yosys_bin = yosys_bin

    def build_flow_single(
        self,
        design: dict[str, Any],
        overwrite: bool = False,
    ) -> None:
        design_dir = self.design_dataset.designs_dir / design["design_name"]
        sources_dir = design_dir / "sources"
        sources_fps = [f for f in sources_dir.iterdir() if f.is_file()]
        sources_fps = [
            f for f in sources_fps if f.suffix in VERILOG_SOURCE_EXTENSIONS_SET
        ]


class ModuleHierarchyFlow(Flow):
    flow_name = "submodule_hierarchy"
    flow_type = "source"

    def build_flow(self, overwrite: bool = False) -> None:
        raise NotImplementedError


class ISEFlow(Flow):
    flow_name = "ise"
    flow_type = "source"

    def build_flow(self, overwrite: bool = False) -> None:
        raise NotImplementedError


class VivadoFlow(Flow):
    flow_name = "vivado"
    flow_type = "source"

    def build_flow(self, overwrite: bool = False) -> None:
        raise NotImplementedError


class OpenRoadFlow(Flow):
    flow_name = "openroad"
    flow_type = "source"

    def build_flow(self, overwrite: bool = False) -> None:
        raise NotImplementedError
