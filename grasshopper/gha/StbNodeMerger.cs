using System;
using System.Collections.Generic;
using System.Globalization;
using Rhino.Geometry;

namespace StbGrasshopper
{
    public sealed class StbNodeMergeResult
    {
        public List<string> Records { get; } = new List<string>();
        public int OriginalNodeCount { get; set; }
        public int UniqueNodeCount { get; set; }
        public int MergedNodeCount => OriginalNodeCount - UniqueNodeCount;
    }

    internal static class StbNodeMerger
    {
        public static StbNodeMergeResult MergeDuplicateNodes(IReadOnlyList<string> records, double tolerance)
        {
            var result = new StbNodeMergeResult();
            if (records == null || records.Count == 0)
            {
                return result;
            }

            var nodeEntries = new List<NodeEntry>();
            var otherRecords = new List<OtherRecord>();

            foreach (var rawLine in records)
            {
                if (string.IsNullOrWhiteSpace(rawLine))
                {
                    continue;
                }

                var line = rawLine.Trim();
                if (line.StartsWith("#", StringComparison.Ordinal))
                {
                    otherRecords.Add(new OtherRecord(line, null));
                    continue;
                }

                var parts = line.Split(',');
                if (parts.Length == 0)
                {
                    continue;
                }

                var recordType = parts[0].Trim();
                if (recordType == "NODE" && TryParseNode(parts, out var nodeId, out var point))
                {
                    nodeEntries.Add(new NodeEntry(nodeId, point, line));
                    continue;
                }

                otherRecords.Add(new OtherRecord(line, recordType));
            }

            result.OriginalNodeCount = nodeEntries.Count;
            if (nodeEntries.Count == 0)
            {
                foreach (var entry in otherRecords)
                {
                    result.Records.Add(entry.Line);
                }
                return result;
            }

            var nodeIdToPoint = new Dictionary<int, Point3d>();

            foreach (var entry in nodeEntries)
            {
                if (nodeIdToPoint.TryGetValue(entry.NodeId, out var existingPoint))
                {
                    if (existingPoint.DistanceTo(entry.Point) > tolerance)
                    {
                        throw new InvalidOperationException(
                            "NODE id "
                            + entry.NodeId
                            + " appears with conflicting coordinates.");
                    }

                    continue;
                }

                nodeIdToPoint[entry.NodeId] = entry.Point;
            }

            var canonicalNodes = new List<CanonicalNode>();
            var idMap = new Dictionary<int, int>();

            foreach (var pair in nodeIdToPoint)
            {
                idMap[pair.Key] = FindOrAddCanonical(canonicalNodes, pair.Value, tolerance);
            }

            result.UniqueNodeCount = canonicalNodes.Count;

            foreach (var canonical in canonicalNodes)
            {
                result.Records.Add(FormatNode(canonical.NodeId, canonical.Point));
            }

            foreach (var entry in otherRecords)
            {
                if (entry.RecordType == null)
                {
                    result.Records.Add(entry.Line);
                    continue;
                }

                result.Records.Add(RemapRecord(entry.Line, entry.RecordType, idMap));
            }

            return result;
        }

        private static int FindOrAddCanonical(List<CanonicalNode> canonicalNodes, Point3d point, double tolerance)
        {
            var canonicalId = FindCanonicalId(canonicalNodes, point, tolerance);
            if (canonicalId >= 0)
            {
                return canonicalId;
            }

            var newId = canonicalNodes.Count + 1;
            canonicalNodes.Add(new CanonicalNode(newId, point));
            return newId;
        }

        private static int FindCanonicalId(List<CanonicalNode> canonicalNodes, Point3d point, double tolerance)
        {
            for (var i = 0; i < canonicalNodes.Count; i++)
            {
                if (canonicalNodes[i].Point.DistanceTo(point) <= tolerance)
                {
                    return canonicalNodes[i].NodeId;
                }
            }

            return -1;
        }

        private static string RemapRecord(string line, string recordType, IReadOnlyDictionary<int, int> idMap)
        {
            var parts = line.Split(',');
            switch (recordType)
            {
                case "ELEM":
                    if (parts.Length >= 4)
                    {
                        parts[2] = RemapField(parts[2], idMap);
                        parts[3] = RemapField(parts[3], idMap);
                    }
                    break;
                case "CONS":
                case "PLOD":
                    if (parts.Length >= 2)
                    {
                        parts[1] = RemapField(parts[1], idMap);
                    }
                    break;
            }

            return string.Join(",", parts);
        }

        private static string RemapField(string field, IReadOnlyDictionary<int, int> idMap)
        {
            var trimmed = field.Trim();
            if (!int.TryParse(trimmed, NumberStyles.Integer, CultureInfo.InvariantCulture, out var nodeId))
            {
                return field;
            }

            if (!idMap.TryGetValue(nodeId, out var mappedId))
            {
                return field;
            }

            return " " + mappedId.ToString(CultureInfo.InvariantCulture);
        }

        private static bool TryParseNode(string[] parts, out int nodeId, out Point3d point)
        {
            nodeId = 0;
            point = Point3d.Unset;
            if (parts.Length < 5)
            {
                return false;
            }

            try
            {
                nodeId = int.Parse(parts[1].Trim(), CultureInfo.InvariantCulture);
                var x = double.Parse(parts[2].Trim(), CultureInfo.InvariantCulture);
                var y = double.Parse(parts[3].Trim(), CultureInfo.InvariantCulture);
                var zText = parts[4].Trim().TrimEnd('*').Trim();
                var z = double.Parse(zText, CultureInfo.InvariantCulture);
                point = new Point3d(x, y, z);
                return true;
            }
            catch (FormatException)
            {
                return false;
            }
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

        private sealed class NodeEntry
        {
            public NodeEntry(int nodeId, Point3d point, string line)
            {
                NodeId = nodeId;
                Point = point;
                Line = line;
            }

            public int NodeId { get; }
            public Point3d Point { get; }
            public string Line { get; }
        }

        private sealed class OtherRecord
        {
            public OtherRecord(string line, string recordType)
            {
                Line = line;
                RecordType = recordType;
            }

            public string Line { get; }
            public string RecordType { get; }
        }

        private sealed class CanonicalNode
        {
            public CanonicalNode(int nodeId, Point3d point)
            {
                NodeId = nodeId;
                Point = point;
            }

            public int NodeId { get; }
            public Point3d Point { get; }
        }
    }
}
