using System.Collections.Generic;
using System.Linq;

namespace StbGrasshopper
{
    internal static class StbLoadCaseFilter
    {
        /// <summary>
        /// Negative loadCase means all load cases.
        /// </summary>
        public static bool Matches(int loadCase, int rowLoadCase)
        {
            return loadCase < 0 || loadCase == rowLoadCase;
        }

        public static List<int> GetLoadCases(StbParsedResults results)
        {
            if (results == null)
            {
                return new List<int>();
            }

            var values = new HashSet<int>();
            foreach (var row in results.Displacements)
            {
                values.Add(row.LoadCase);
            }

            foreach (var row in results.Reactions)
            {
                values.Add(row.LoadCase);
            }

            foreach (var row in results.ElementForces)
            {
                values.Add(row.LoadCase);
            }

            return values.OrderBy(v => v).ToList();
        }
    }
}
