using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.IO;
using Grasshopper.Kernel;
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

    public sealed class StbNodeComponent : GH_Component
    {
        public StbNodeComponent() : base("STB Node", "STB Node", "Create NODE records from points.", "STB", "Model") { }
        public override Guid ComponentGuid => new Guid("466e891d-870e-4044-88d5-b9d0949639fa");

        protected override Bitmap Icon => StbIcons.Node;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddIntegerParameter("Start ID", "ID", "First node id.", GH_ParamAccess.item, 1);
            pManager.AddPointParameter("Points", "P", "Node coordinates in meters.", GH_ParamAccess.list);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddIntegerParameter("Node IDs", "N", "Generated node ids.", GH_ParamAccess.list);
            pManager.AddPointParameter("Points", "P", "Original node points passed through.", GH_ParamAccess.list);
            pManager.AddTextParameter("Records", "Rec", "STB NODE records.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            int startId = 1;
            var points = new List<Point3d>();
            da.GetData(0, ref startId);
            if (!da.GetDataList(1, points)) return;

            var ids = new List<int>();
            var records = new List<string>();
            for (var i = 0; i < points.Count; i++)
            {
                var id = startId + i;
                ids.Add(id);
                var p = points[i];
                records.Add("NODE," + id + "," + StbRecord.Number(p.X) + "," + StbRecord.Number(p.Y) + "," + StbRecord.Number(p.Z));
            }

            da.SetDataList(0, ids);
            da.SetDataList(1, points);
            da.SetDataList(2, records);
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

    public sealed class StbBeamComponent : GH_Component
    {
        public StbBeamComponent() : base("STB Beam", "STB Beam", "Create ELEM records from node id pairs.", "STB", "Model") { }
        public override Guid ComponentGuid => new Guid("e9ac94fe-4ee4-4d15-b16b-7881e3b1f622");

        protected override Bitmap Icon => StbIcons.Beam;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddIntegerParameter("Start ID", "ID", "First element id.", GH_ParamAccess.item, 1);
            pManager.AddIntegerParameter("Node I", "I", "Start node ids.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("Node J", "J", "End node ids.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("Section ID", "Sec", "Section id.", GH_ParamAccess.item, 1);
            pManager.AddNumberParameter("Beta", "Beta", "Section beta angle in degrees.", GH_ParamAccess.item, 0.0);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddIntegerParameter("Element IDs", "E", "Generated element ids.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("Node I", "I", "Start node ids.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("Node J", "J", "End node ids.", GH_ParamAccess.list);
            pManager.AddTextParameter("Records", "Rec", "STB ELEM records.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            int startId = 1;
            int sectionId = 1;
            double beta = 0.0;
            var nodeI = new List<int>();
            var nodeJ = new List<int>();
            da.GetData(0, ref startId);
            if (!da.GetDataList(1, nodeI)) return;
            if (!da.GetDataList(2, nodeJ)) return;
            da.GetData(3, ref sectionId);
            da.GetData(4, ref beta);

            var count = Math.Min(nodeI.Count, nodeJ.Count);
            var ids = new List<int>();
            var records = new List<string>();
            for (var i = 0; i < count; i++)
            {
                var id = startId + i;
                ids.Add(id);
                records.Add("ELEM," + id + "," + nodeI[i] + "," + nodeJ[i] + "," + sectionId + "," + StbRecord.Number(beta));
            }

            da.SetDataList(0, ids);
            da.SetDataList(1, nodeI.GetRange(0, count));
            da.SetDataList(2, nodeJ.GetRange(0, count));
            da.SetDataList(3, records);
        }
    }

    public sealed class StbMaterialComponent : GH_Component
    {
        public StbMaterialComponent() : base("STB Material", "STB Mat", "Create one MATE record.", "STB", "Model") { }
        public override Guid ComponentGuid => new Guid("2c6d678d-92f9-4ee5-a171-e95d64b1411b");

        protected override Bitmap Icon => StbIcons.Material;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddIntegerParameter("ID", "ID", "Material id.", GH_ParamAccess.item, 1);
            pManager.AddTextParameter("Name", "Name", "Material name.", GH_ParamAccess.item, "MAT");
            pManager.AddNumberParameter("E", "E", "Young's modulus in N/mm2.", GH_ParamAccess.item, 205000.0);
            pManager.AddNumberParameter("G", "G", "Shear modulus in N/mm2.", GH_ParamAccess.item, 79000.0);
            pManager.AddNumberParameter("Gamma", "Gamma", "Unit weight in kN/m3.", GH_ParamAccess.item, 78.5);
            pManager.AddNumberParameter("Alpha", "Alpha", "Thermal expansion coefficient.", GH_ParamAccess.item, 0.0);
            pManager.AddNumberParameter("Fy", "Fy", "Yield stress in N/mm2.", GH_ParamAccess.item, 235.0);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddTextParameter("Record", "Rec", "STB MATE record.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            int id = 1;
            string name = "MAT";
            double e = 205000.0, g = 79000.0, gamma = 78.5, alpha = 0.0, fy = 235.0;
            da.GetData(0, ref id);
            da.GetData(1, ref name);
            da.GetData(2, ref e);
            da.GetData(3, ref g);
            da.GetData(4, ref gamma);
            da.GetData(5, ref alpha);
            da.GetData(6, ref fy);
            da.SetData(0, "MATE," + id + "," + name + "," + StbRecord.Number(e) + "," + StbRecord.Number(g) + "," + StbRecord.Number(gamma) + "," + StbRecord.Number(alpha) + "," + StbRecord.Number(fy));
        }
    }

    public sealed class StbSectionComponent : GH_Component
    {
        public StbSectionComponent() : base("STB Section", "STB Sec", "Create one SECT record.", "STB", "Model") { }
        public override Guid ComponentGuid => new Guid("fd94f3c4-1574-45dc-bd80-6635f18517dd");

        protected override Bitmap Icon => StbIcons.Section;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddIntegerParameter("ID", "ID", "Section id.", GH_ParamAccess.item, 1);
            pManager.AddTextParameter("Name", "Name", "Section name.", GH_ParamAccess.item, "SEC");
            pManager.AddIntegerParameter("Material ID", "Mat", "Material id.", GH_ParamAccess.item, 1);
            pManager.AddIntegerParameter("Type", "Type", "0 rectangle, 1 circle, 2 I, 3 CHS, 4 RHS.", GH_ParamAccess.item, 0);
            pManager.AddNumberParameter("Dimensions", "Dim", "Section dimensions in mm.", GH_ParamAccess.list);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddTextParameter("Record", "Rec", "STB SECT record.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            int id = 1, matId = 1, type = 0;
            string name = "SEC";
            var dims = new List<double>();
            da.GetData(0, ref id);
            da.GetData(1, ref name);
            da.GetData(2, ref matId);
            da.GetData(3, ref type);
            da.GetDataList(4, dims);

            var fields = new List<string> { "SECT", id.ToString(), name, matId.ToString(), type.ToString() };
            foreach (var dim in dims)
            {
                fields.Add(StbRecord.Number(dim));
            }
            da.SetData(0, string.Join(",", fields));
        }
    }

    public sealed class StbSupportComponent : GH_Component
    {
        public StbSupportComponent() : base("STB Support", "STB Sup", "Create CONS support records.", "STB", "Model") { }
        public override Guid ComponentGuid => new Guid("54816191-f022-43a1-b094-9bb5cf4bc371");

        protected override Bitmap Icon => StbIcons.Support;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddIntegerParameter("Node IDs", "N", "Supported node ids.", GH_ParamAccess.list);
            pManager.AddBooleanParameter("TX", "TX", "Fix translation X.", GH_ParamAccess.item, true);
            pManager.AddBooleanParameter("TY", "TY", "Fix translation Y.", GH_ParamAccess.item, true);
            pManager.AddBooleanParameter("TZ", "TZ", "Fix translation Z.", GH_ParamAccess.item, true);
            pManager.AddBooleanParameter("RX", "RX", "Fix rotation X.", GH_ParamAccess.item, true);
            pManager.AddBooleanParameter("RY", "RY", "Fix rotation Y.", GH_ParamAccess.item, true);
            pManager.AddBooleanParameter("RZ", "RZ", "Fix rotation Z.", GH_ParamAccess.item, true);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddTextParameter("Records", "Rec", "STB CONS records.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            var nodeIds = new List<int>();
            bool tx = true, ty = true, tz = true, rx = true, ry = true, rz = true;
            if (!da.GetDataList(0, nodeIds)) return;
            da.GetData(1, ref tx);
            da.GetData(2, ref ty);
            da.GetData(3, ref tz);
            da.GetData(4, ref rx);
            da.GetData(5, ref ry);
            da.GetData(6, ref rz);

            var records = new List<string>();
            foreach (var nodeId in nodeIds)
            {
                records.Add("CONS," + nodeId + "," + Bit(tx) + "," + Bit(ty) + "," + Bit(tz) + "," + Bit(rx) + "," + Bit(ry) + "," + Bit(rz));
            }
            da.SetDataList(0, records);
        }

        private static int Bit(bool value) => value ? 1 : 0;
    }

    public sealed class StbLoadComponent : GH_Component
    {
        public StbLoadComponent() : base("STB Load", "STB Load", "Create PLOD point load records.", "STB", "Model") { }
        public override Guid ComponentGuid => new Guid("fcf0fb0e-33d0-4926-a09f-1f1bbffcfbc1");

        protected override Bitmap Icon => StbIcons.Load;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddIntegerParameter("Node IDs", "N", "Loaded node ids.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("Load Case", "LC", "Load case id.", GH_ParamAccess.item, 0);
            pManager.AddVectorParameter("Force", "F", "Force vector in kN.", GH_ParamAccess.item, Vector3d.Zero);
            pManager.AddVectorParameter("Moment", "M", "Moment vector in kNm.", GH_ParamAccess.item, Vector3d.Zero);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddTextParameter("Records", "Rec", "STB PLOD records.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            var nodeIds = new List<int>();
            int loadCase = 0;
            var force = Vector3d.Zero;
            var moment = Vector3d.Zero;
            if (!da.GetDataList(0, nodeIds)) return;
            da.GetData(1, ref loadCase);
            da.GetData(2, ref force);
            da.GetData(3, ref moment);

            var records = new List<string>();
            foreach (var nodeId in nodeIds)
            {
                records.Add("PLOD," + nodeId + "," + loadCase + "," + StbRecord.Number(force.X) + "," + StbRecord.Number(force.Y) + "," + StbRecord.Number(force.Z) + "," + StbRecord.Number(moment.X) + "," + StbRecord.Number(moment.Y) + "," + StbRecord.Number(moment.Z));
            }
            da.SetDataList(0, records);
        }
    }

    public sealed class StbAssembleModelComponent : GH_Component
    {
        public StbAssembleModelComponent() : base("STB Assemble Model", "STB Model", "Assemble STB records and optionally write a .dat file.", "STB", "Model") { }
        public override Guid ComponentGuid => new Guid("ce8a157a-b1b7-4d92-918f-e6ce2294af1c");

        protected override Bitmap Icon => StbIcons.Assemble;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddTextParameter("Records", "Rec", "STB record lines.", GH_ParamAccess.list);
            pManager.AddTextParameter("DAT Path", "DAT", "Optional .dat path to write.", GH_ParamAccess.item, string.Empty);
            pManager.AddBooleanParameter("Write", "Write", "Write the .dat file.", GH_ParamAccess.item, false);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddTextParameter("Text", "Text", "Assembled STB input text.", GH_ParamAccess.item);
            pManager.AddTextParameter("DAT Path", "DAT", "Written .dat path.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            var records = new List<string>();
            string datPath = string.Empty;
            bool write = false;
            if (!da.GetDataList(0, records)) return;
            da.GetData(1, ref datPath);
            da.GetData(2, ref write);

            var text = string.Join(Environment.NewLine, records) + Environment.NewLine;
            if (write && !string.IsNullOrWhiteSpace(datPath))
            {
                var fullPath = Path.GetFullPath(datPath);
                Directory.CreateDirectory(Path.GetDirectoryName(fullPath));
                File.WriteAllText(fullPath, text);
                datPath = fullPath;
            }

            da.SetData(0, text);
            da.SetData(1, datPath);
        }
    }
}
