using System;
using System.Collections.Generic;
using System.Drawing;
using Grasshopper.Kernel;
using Rhino.Geometry;

namespace StbGrasshopper
{
    public sealed class StbDeformedShapeComponent : GH_Component
    {
        public StbDeformedShapeComponent()
            : base(
                "STB Deformed Shape",
                "STB Def",
                "Create deformed points and member line segments from STB results.",
                "STB",
                "Results")
        {
        }

        public override Guid ComponentGuid => new Guid("da5d7290-dd2e-4e49-a21a-db2420f7f59a");

        protected override Bitmap Icon => StbIcons.DeformedShape;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddGenericParameter("Results", "R", "Parsed STB result object from STB Analyze.", GH_ParamAccess.item);
            pManager.AddIntegerParameter("Load Case", "LC", "Load case to display. Negative means all load cases.", GH_ParamAccess.item, 0);
            pManager.AddNumberParameter("Scale", "Scale", "Displacement scale factor.", GH_ParamAccess.item, 1.0);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddPointParameter("Deformed Points", "Pd", "Deformed node points.", GH_ParamAccess.list);
            pManager.AddLineParameter("Deformed Lines", "Ld", "Deformed member line segments.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("Node IDs", "N", "Node ids for deformed points.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            StbParsedResults results = null;
            int loadCase = 0;
            double scale = 1.0;

            if (!da.GetData(0, ref results) || results == null)
            {
                return;
            }

            da.GetData(1, ref loadCase);
            da.GetData(2, ref scale);

            if (results.Nodes.Count == 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Error,
                    "Results contain no node geometry. Re-run STB Analyze with the same .dat file.");
                return;
            }

            var translationById = BuildTranslationLookup(results, loadCase);
            if (loadCase >= 0 && translationById.Count == 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Warning,
                    "No displacement rows found for load case " + loadCase + ".");
            }

            var deformedById = new Dictionary<int, Point3d>();
            var deformedPoints = new List<Point3d>();
            var nodeIds = new List<int>();

            foreach (var node in results.Nodes)
            {
                translationById.TryGetValue(node.NodeId, out var translation);
                var deformed = node.Point + translation * scale;
                deformedById[node.NodeId] = deformed;
                deformedPoints.Add(deformed);
                nodeIds.Add(node.NodeId);
            }

            var deformedLines = BuildDeformedLines(deformedById, results.Elements);

            da.SetDataList(0, deformedPoints);
            da.SetDataList(1, deformedLines);
            da.SetDataList(2, nodeIds);
        }

        private static Dictionary<int, Vector3d> BuildTranslationLookup(StbParsedResults results, int loadCase)
        {
            var translationById = new Dictionary<int, Vector3d>();

            foreach (var row in results.Displacements)
            {
                if (!StbLoadCaseFilter.Matches(loadCase, row.LoadCase))
                {
                    continue;
                }

                translationById[row.NodeId] = new Vector3d(row.X, row.Y, row.Z);
            }

            return translationById;
        }

        private static List<Line> BuildDeformedLines(
            Dictionary<int, Point3d> deformedById,
            List<StbElementGeometry> elements)
        {
            var lines = new List<Line>();

            foreach (var element in elements)
            {
                if (!deformedById.TryGetValue(element.NodeI, out var p0))
                {
                    continue;
                }

                if (!deformedById.TryGetValue(element.NodeJ, out var p1))
                {
                    continue;
                }

                lines.Add(new Line(p0, p1));
            }

            return lines;
        }
    }
}
