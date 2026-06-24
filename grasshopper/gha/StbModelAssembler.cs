using System;
using System.Collections.Generic;
using Rhino.Geometry;

namespace StbGrasshopper
{
    public sealed class StbAssembleResult
    {
        public string Text { get; set; } = string.Empty;
        public int UniqueNodeCount { get; set; }
        public int MergedNodeCount { get; set; }
    }

    internal static class StbModelAssembler
    {
        private const double PropertyTolerance = 1e-6;

        public static StbAssembleResult Assemble(
            IReadOnlyList<StbElementModel> elements,
            IReadOnlyList<StbLoadModel> loads,
            IReadOnlyList<StbSupportModel> supports,
            double tolerance)
        {
            var result = new StbAssembleResult();
            if (elements == null || elements.Count == 0)
            {
                return result;
            }

            var materials = new List<StbMaterialModel>();
            var materialIds = new Dictionary<StbMaterialModel, int>(ReferenceEqualityComparer<StbMaterialModel>.Instance);
            var sections = new List<StbSectionModel>();
            var sectionIds = new Dictionary<StbSectionModel, int>(ReferenceEqualityComparer<StbSectionModel>.Instance);

            foreach (var element in elements)
            {
                if (element?.Section == null)
                {
                    throw new InvalidOperationException("Element '" + element?.Name + "' has no section.");
                }

                if (element.Section.Material == null)
                {
                    throw new InvalidOperationException("Section '" + element.Section.Name + "' has no material.");
                }

                StbSectionDimensions.Resolve(
                    element.Section.Type,
                    element.Section.Dimensions,
                    useDefaultsWhenEmpty: false);

                AssignMaterialId(element.Section.Material, materials, materialIds);
                AssignSectionId(element.Section, sections, sectionIds, materials, materialIds);
            }

            var materialRecords = new List<string>();
            foreach (var material in materials)
            {
                materialRecords.Add(material.ToMateRecord(materialIds[material]));
            }

            var sectionRecords = new List<string>();
            foreach (var section in sections)
            {
                sectionRecords.Add(section.ToSectRecord(sectionIds[section], materialIds[section.Material]));
            }

            var geometryRecords = new List<string>();
            var nextNodeId = 1;
            var nextElemId = 1;

            foreach (var element in elements)
            {
                if (!element.Line.IsValid)
                {
                    continue;
                }

                var nodeI = nextNodeId++;
                var nodeJ = nextNodeId++;

                geometryRecords.Add(FormatNode(nodeI, element.Line.From));
                geometryRecords.Add(FormatNode(nodeJ, element.Line.To));
                geometryRecords.Add(
                    "ELEM,"
                    + nextElemId++
                    + ","
                    + nodeI
                    + ","
                    + nodeJ
                    + ","
                    + sectionIds[element.Section]
                    + ","
                    + StbRecord.Number(element.Beta));
            }

            var mergeResult = StbNodeMerger.MergeDuplicateNodes(geometryRecords, tolerance);
            result.UniqueNodeCount = mergeResult.UniqueNodeCount;
            result.MergedNodeCount = mergeResult.MergedNodeCount;

            var finalRecords = new List<string>();
            finalRecords.AddRange(materialRecords);
            finalRecords.AddRange(sectionRecords);
            finalRecords.AddRange(mergeResult.Records);

            var canonicalNodes = ExtractCanonicalNodes(mergeResult.Records);
            foreach (var support in supports ?? Array.Empty<StbSupportModel>())
            {
                var nodeId = FindNodeId(support.Point, canonicalNodes, tolerance);
                finalRecords.Add(support.ToConsRecord(nodeId));
            }

            foreach (var load in loads ?? Array.Empty<StbLoadModel>())
            {
                var nodeId = FindNodeId(load.Point, canonicalNodes, tolerance);
                finalRecords.Add(load.ToPlodRecord(nodeId));
            }

            result.Text = string.Join(Environment.NewLine, finalRecords) + Environment.NewLine;
            return result;
        }

        private static void AssignMaterialId(
            StbMaterialModel material,
            List<StbMaterialModel> materials,
            Dictionary<StbMaterialModel, int> materialIds)
        {
            foreach (var existing in materials)
            {
                if (existing.Matches(material, PropertyTolerance))
                {
                    materialIds[material] = materialIds[existing];
                    return;
                }
            }

            var id = materials.Count + 1;
            materials.Add(material);
            materialIds[material] = id;
        }

        private static void AssignSectionId(
            StbSectionModel section,
            List<StbSectionModel> sections,
            Dictionary<StbSectionModel, int> sectionIds,
            List<StbMaterialModel> materials,
            Dictionary<StbMaterialModel, int> materialIds)
        {
            foreach (var existing in sections)
            {
                if (existing.Matches(section, PropertyTolerance))
                {
                    sectionIds[section] = sectionIds[existing];
                    return;
                }
            }

            var id = sections.Count + 1;
            sections.Add(section);
            sectionIds[section] = id;
        }

        private static List<(int NodeId, Point3d Point)> ExtractCanonicalNodes(IReadOnlyList<string> records)
        {
            var nodes = new List<(int NodeId, Point3d Point)>();
            foreach (var rawLine in records)
            {
                if (string.IsNullOrWhiteSpace(rawLine))
                {
                    continue;
                }

                var parts = rawLine.Trim().Split(',');
                if (parts.Length < 5 || parts[0].Trim() != "NODE")
                {
                    continue;
                }

                if (int.TryParse(parts[1].Trim(), out var nodeId)
                    && double.TryParse(parts[2].Trim(), System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var x)
                    && double.TryParse(parts[3].Trim(), System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var y)
                    && double.TryParse(parts[4].Trim().TrimEnd('*').Trim(), System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var z))
                {
                    nodes.Add((nodeId, new Point3d(x, y, z)));
                }
            }

            return nodes;
        }

        private static int FindNodeId(Point3d point, IReadOnlyList<(int NodeId, Point3d Point)> nodes, double tolerance)
        {
            for (var i = 0; i < nodes.Count; i++)
            {
                if (nodes[i].Point.DistanceTo(point) <= tolerance)
                {
                    return nodes[i].NodeId;
                }
            }

            throw new InvalidOperationException("No node found near " + point + " within tolerance " + StbRecord.Number(tolerance) + ".");
        }

        private static string FormatNode(int nodeId, Point3d point)
        {
            return "NODE,"
                + nodeId
                + ","
                + StbRecord.Number(point.X)
                + ","
                + StbRecord.Number(point.Y)
                + ","
                + StbRecord.Number(point.Z);
        }

        private sealed class ReferenceEqualityComparer<T> : IEqualityComparer<T>
            where T : class
        {
            public static ReferenceEqualityComparer<T> Instance { get; } = new ReferenceEqualityComparer<T>();

            public bool Equals(T x, T y) => ReferenceEquals(x, y);

            public int GetHashCode(T obj) => obj == null ? 0 : System.Runtime.CompilerServices.RuntimeHelpers.GetHashCode(obj);
        }
    }
}
