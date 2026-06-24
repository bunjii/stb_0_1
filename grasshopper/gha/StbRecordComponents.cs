using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.IO;
using Grasshopper.Kernel;
using Rhino;
using Rhino.Geometry;

namespace StbGrasshopper
{
    internal static class StbRecord
    {
        public static string Number(double value)
        {
            return value.ToString("0.##########", CultureInfo.InvariantCulture);
        }
    }

    public sealed class StbDatNodesComponent : GH_Component
    {
        public StbDatNodesComponent() : base("STB DAT Nodes", "STB DAT Nodes", "Read NODE records from an existing STB .dat file.", "STB", "Model") { }
        public override Guid ComponentGuid => new Guid("279ef031-21dd-4fda-b262-baa1e473a66f");

        protected override Bitmap Icon => StbIcons.DatNodes;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddTextParameter("DAT Path", "DAT", "Path to the STB .dat file.", GH_ParamAccess.item);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddIntegerParameter("Node IDs", "N", "Node ids read from NODE records.", GH_ParamAccess.list);
            pManager.AddPointParameter("Points", "P", "Original node coordinates in meters.", GH_ParamAccess.list);
            pManager.AddTextParameter("Records", "Rec", "NODE records read from the file.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            string datPath = null;
            if (!da.GetData(0, ref datPath)) return;

            if (string.IsNullOrWhiteSpace(datPath) || !File.Exists(datPath))
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "DAT file not found: " + datPath);
                return;
            }

            StbDatParser.ReadGeometry(datPath, out var parsedNodes, out _);

            var nodeIds = new List<int>();
            var points = new List<Point3d>();
            var records = new List<string>();

            foreach (var node in parsedNodes)
            {
                nodeIds.Add(node.NodeId);
                points.Add(node.Point);
                records.Add(
                    "NODE,"
                    + node.NodeId
                    + ","
                    + StbRecord.Number(node.Point.X)
                    + ","
                    + StbRecord.Number(node.Point.Y)
                    + ","
                    + StbRecord.Number(node.Point.Z));
            }

            da.SetDataList(0, nodeIds);
            da.SetDataList(1, points);
            da.SetDataList(2, records);
        }
    }

    public sealed class StbDatBeamsComponent : GH_Component
    {
        public StbDatBeamsComponent() : base("STB DAT Beams", "STB DAT Beams", "Read ELEM records from an existing STB .dat file.", "STB", "Model") { }
        public override Guid ComponentGuid => new Guid("8b2f4a19-6c3d-4f0a-9f1e-2d8b7a4c1e03");

        protected override Bitmap Icon => StbIcons.DatBeams;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddTextParameter("DAT Path", "DAT", "Path to the STB .dat file.", GH_ParamAccess.item);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddIntegerParameter("Element IDs", "E", "Element ids read from ELEM records.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("Node I", "I", "Start node ids.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("Node J", "J", "End node ids.", GH_ParamAccess.list);
            pManager.AddTextParameter("Records", "Rec", "ELEM records read from the file.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            string datPath = null;
            if (!da.GetData(0, ref datPath)) return;

            if (string.IsNullOrWhiteSpace(datPath) || !File.Exists(datPath))
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "DAT file not found: " + datPath);
                return;
            }

            StbDatParser.ReadGeometry(datPath, out _, out var parsedElements);

            var elementIds = new List<int>();
            var nodeI = new List<int>();
            var nodeJ = new List<int>();
            var records = new List<string>();

            foreach (var element in parsedElements)
            {
                elementIds.Add(element.ElementId);
                nodeI.Add(element.NodeI);
                nodeJ.Add(element.NodeJ);
                records.Add("ELEM," + element.ElementId + "," + element.NodeI + "," + element.NodeJ + ",0,0");
            }

            da.SetDataList(0, elementIds);
            da.SetDataList(1, nodeI);
            da.SetDataList(2, nodeJ);
            da.SetDataList(3, records);
        }
    }

    public sealed class StbElementComponent : GH_Component
    {
        public StbElementComponent() : base("STB Element", "STB Elem", "Create an STB element from a line and section.", "STB", "Model") { }
        public override Guid ComponentGuid => new Guid("e9ac94fe-4ee4-4d15-b16b-7881e3b1f622");

        protected override Bitmap Icon => StbIcons.Beam;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddTextParameter("Name", "Name", "Element name.", GH_ParamAccess.item, "ELEM");
            pManager.AddLineParameter("Line", "L", "Element center line.", GH_ParamAccess.item);
            pManager.AddParameter(new StbSectionParameter(), "Section", "Sec", "Section definition.", GH_ParamAccess.item);
            pManager.AddNumberParameter("Beta", "Beta", "Section beta angle in degrees.", GH_ParamAccess.item, 0.0);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbElementParameter(), "Element", "Elem", "STB element object.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            string name = "ELEM";
            var line = Line.Unset;
            double beta = 0.0;
            da.GetData(0, ref name);
            if (!da.GetData(1, ref line)) return;
            if (!StbModelGooUtil.TryGetSection(da, 2, out var section)) return;
            da.GetData(3, ref beta);

            if (!line.IsValid)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Invalid line.");
                return;
            }

            var element = new StbElementModel
            {
                Name = name,
                Line = line,
                Section = section,
                Beta = beta,
            };

            da.SetData(0, new StbElementGoo(element));
        }
    }

    public sealed class StbMaterialComponent : GH_Component
    {
        public StbMaterialComponent() : base("STB Material", "STB Mat", "Create an STB material object.", "STB", "Model") { }
        public override Guid ComponentGuid => new Guid("2c6d678d-92f9-4ee5-a171-e95d64b1411b");

        protected override Bitmap Icon => StbIcons.Material;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddTextParameter("Name", "Name", "Material name.", GH_ParamAccess.item, "MAT");
            pManager.AddNumberParameter("E", "E", "Young's modulus in N/mm2.", GH_ParamAccess.item, 205000.0);
            pManager.AddNumberParameter("G", "G", "Shear modulus in N/mm2.", GH_ParamAccess.item, 79000.0);
            pManager.AddNumberParameter("Gamma", "Gamma", "Unit weight in kN/m3.", GH_ParamAccess.item, 78.5);
            pManager.AddNumberParameter("Alpha", "Alpha", "Thermal expansion coefficient.", GH_ParamAccess.item, 0.0);
            pManager.AddNumberParameter("Fy", "Fy", "Yield stress in N/mm2.", GH_ParamAccess.item, 235.0);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbMaterialParameter(), "Mat", "Mat", "STB material object.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            string name = "MAT";
            double e = 205000.0, g = 79000.0, gamma = 78.5, alpha = 0.0, fy = 235.0;
            da.GetData(0, ref name);
            da.GetData(1, ref e);
            da.GetData(2, ref g);
            da.GetData(3, ref gamma);
            da.GetData(4, ref alpha);
            da.GetData(5, ref fy);

            da.SetData(0, new StbMaterialGoo(new StbMaterialModel
            {
                Name = name,
                E = e,
                G = g,
                Gamma = gamma,
                Alpha = alpha,
                Fy = fy,
            }));
        }
    }

    public sealed class StbSectionComponent : GH_Component
    {
        public StbSectionComponent() : base("STB Section", "STB Sec", "Create an STB section object.", "STB", "Model") { }
        public override Guid ComponentGuid => new Guid("fd94f3c4-1574-45dc-bd80-6635f18517dd");

        protected override Bitmap Icon => StbIcons.Section;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddTextParameter("Name", "Name", "Section name.", GH_ParamAccess.item, "SEC");
            pManager.AddParameter(new StbMaterialParameter(), "Mat", "Mat", "Material definition.", GH_ParamAccess.item);
            pManager.AddIntegerParameter("Type", "Type", "0 rectangle, 1 circle, 2 I, 3 CHS, 4 RHS.", GH_ParamAccess.item, 0);
            pManager.AddNumberParameter("Dim", "Dim", "Section dimensions in mm. Type 0: B,H. Type 1: D. Type 2/4: H,B,tw,tf or H,B,t,t. Type 3: D,t.", GH_ParamAccess.list);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbSectionParameter(), "Section", "Sec", "STB section object.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            int type = 0;
            string name = "SEC";
            var dims = new List<double>();
            da.GetData(0, ref name);
            if (!StbModelGooUtil.TryGetMaterial(da, 1, out var material)) return;
            da.GetData(2, ref type);
            da.GetDataList(3, dims);

            List<double> resolvedDims;
            try
            {
                resolvedDims = StbSectionDimensions.Resolve(type, dims, useDefaultsWhenEmpty: true);
            }
            catch (InvalidOperationException ex)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, ex.Message);
                return;
            }

            if (dims.Count == 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Remark,
                    "Dim was empty. Using defaults for type "
                    + type
                    + ": "
                    + string.Join(", ", resolvedDims)
                    + " mm.");
            }

            var section = new StbSectionModel
            {
                Name = name,
                Material = material,
                Type = type,
            };
            section.Dimensions.AddRange(resolvedDims);

            da.SetData(0, new StbSectionGoo(section));
        }
    }

    public sealed class StbSupportComponent : GH_Component
    {
        public StbSupportComponent() : base("STB Support", "STB Sup", "Create STB support objects from points.", "STB", "Model") { }
        public override Guid ComponentGuid => new Guid("54816191-f022-43a1-b094-9bb5cf4bc371");

        protected override Bitmap Icon => StbIcons.Support;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddPointParameter("Point", "P", "Support location in meters.", GH_ParamAccess.list);
            pManager.AddBooleanParameter("TX", "TX", "Fix translation X.", GH_ParamAccess.item, true);
            pManager.AddBooleanParameter("TY", "TY", "Fix translation Y.", GH_ParamAccess.item, true);
            pManager.AddBooleanParameter("TZ", "TZ", "Fix translation Z.", GH_ParamAccess.item, true);
            pManager.AddBooleanParameter("RX", "RX", "Fix rotation X.", GH_ParamAccess.item, true);
            pManager.AddBooleanParameter("RY", "RY", "Fix rotation Y.", GH_ParamAccess.item, true);
            pManager.AddBooleanParameter("RZ", "RZ", "Fix rotation Z.", GH_ParamAccess.item, true);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbSupportParameter(), "Support", "Sup", "STB support objects.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            var points = new List<Point3d>();
            bool tx = true, ty = true, tz = true, rx = true, ry = true, rz = true;
            if (!da.GetDataList(0, points)) return;
            da.GetData(1, ref tx);
            da.GetData(2, ref ty);
            da.GetData(3, ref tz);
            da.GetData(4, ref rx);
            da.GetData(5, ref ry);
            da.GetData(6, ref rz);

            var supports = new List<StbSupportGoo>();
            foreach (var point in points)
            {
                supports.Add(new StbSupportGoo(new StbSupportModel
                {
                    Point = point,
                    Tx = tx,
                    Ty = ty,
                    Tz = tz,
                    Rx = rx,
                    Ry = ry,
                    Rz = rz,
                }));
            }

            da.SetDataList(0, supports);
        }
    }

    public sealed class StbLoadComponent : GH_Component
    {
        public StbLoadComponent() : base("STB Load", "STB Load", "Create STB point load objects from points.", "STB", "Model") { }
        public override Guid ComponentGuid => new Guid("fcf0fb0e-33d0-4926-a09f-1f1bbffcfbc1");

        protected override Bitmap Icon => StbIcons.Load;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddPointParameter("Point", "P", "Loaded point in meters.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("LC", "LC", "Load case id.", GH_ParamAccess.item, 0);
            pManager.AddVectorParameter("F", "F", "Force vector in kN.", GH_ParamAccess.item, Vector3d.Zero);
            pManager.AddVectorParameter("M", "M", "Moment vector in kNm.", GH_ParamAccess.item, Vector3d.Zero);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbLoadParameter(), "Load", "Ld", "STB load objects.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            var points = new List<Point3d>();
            int loadCase = 0;
            var force = Vector3d.Zero;
            var moment = Vector3d.Zero;
            if (!da.GetDataList(0, points)) return;
            da.GetData(1, ref loadCase);
            da.GetData(2, ref force);
            da.GetData(3, ref moment);

            var loads = new List<StbLoadGoo>();
            foreach (var point in points)
            {
                loads.Add(new StbLoadGoo(new StbLoadModel
                {
                    Point = point,
                    LoadCase = loadCase,
                    Force = force,
                    Moment = moment,
                }));
            }

            da.SetDataList(0, loads);
        }
    }

    public sealed class StbAssembleModelComponent : GH_Component
    {
        public StbAssembleModelComponent() : base("STB Assemble Model", "STB Model", "Assemble typed STB model objects into a .dat text file.", "STB", "Model") { }
        public override Guid ComponentGuid => new Guid("ce8a157a-b1b7-4d92-918f-e6ce2294af1c");

        protected override Bitmap Icon => StbIcons.Assemble;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbElementParameter(), "Element", "Elem", "STB elements.", GH_ParamAccess.list);
            pManager.AddParameter(new StbLoadParameter(), "Load", "Ld", "STB loads.", GH_ParamAccess.list);
            pManager.AddParameter(new StbSupportParameter(), "Support", "Sup", "STB supports.", GH_ParamAccess.list);
            pManager.AddTextParameter("DAT", "DAT", "Output .dat path. Empty uses the temp folder.", GH_ParamAccess.item, string.Empty);
            pManager.AddBooleanParameter("Write", "Write", "Write the .dat file.", GH_ParamAccess.item, false);
            Params.Input[1].Optional = true;
            Params.Input[2].Optional = true;
            Params.Input[3].Optional = true;
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddTextParameter("Text", "Text", "Assembled STB input text.", GH_ParamAccess.item);
            pManager.AddTextParameter("DAT", "DAT", "Resolved .dat path. Populated when Write is true.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            var elements = StbModelGooUtil.GetElements(da, 0);
            var loads = StbModelGooUtil.GetLoads(da, 1);
            var supports = StbModelGooUtil.GetSupports(da, 2);
            string datPath = string.Empty;
            bool write = false;
            da.GetData(3, ref datPath);
            da.GetData(4, ref write);

            if (elements.Count == 0)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "At least one element is required.");
                return;
            }

            var tolerance = RhinoDoc.ActiveDoc?.ModelAbsoluteTolerance ?? 0.001;

            StbAssembleResult assembleResult;
            try
            {
                assembleResult = StbModelAssembler.Assemble(elements, loads, supports, tolerance);
            }
            catch (InvalidOperationException ex)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, ex.Message);
                return;
            }

            if (assembleResult.MergedNodeCount > 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Remark,
                    "Merged "
                    + assembleResult.MergedNodeCount
                    + " duplicate node(s) at tolerance "
                    + StbRecord.Number(tolerance)
                    + ".");
            }

            var writtenPath = string.Empty;
            if (write)
            {
                try
                {
                    writtenPath = StbPathUtil.WriteTextFile(datPath, assembleResult.Text);
                }
                catch (Exception ex)
                {
                    AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Failed to write .dat file: " + ex.Message);
                    return;
                }
            }
            else
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Remark,
                    "Write is false. Set Write to true before connecting DAT to STB Analyze.");
            }

            da.SetData(0, assembleResult.Text);
            da.SetData(1, writtenPath);
        }
    }
}
