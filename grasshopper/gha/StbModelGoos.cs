using System;
using System.Collections.Generic;
using System.Drawing;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Types;

namespace StbGrasshopper
{
    public sealed class StbMaterialGoo : GH_Goo<StbMaterialModel>
    {
        public StbMaterialGoo()
        {
        }

        public StbMaterialGoo(StbMaterialModel material)
        {
            Value = material;
        }

        public override bool IsValid => Value != null;

        public override string TypeName => "STB Material";

        public override string TypeDescription => "STB material definition";

        public override IGH_Goo Duplicate()
        {
            return new StbMaterialGoo(Value?.Duplicate());
        }

        public override string ToString()
        {
            return Value?.ToString() ?? "Null STB Material";
        }

        public override bool CastFrom(object source)
        {
            if (source is StbMaterialModel material)
            {
                Value = material;
                return true;
            }

            if (source is StbMaterialGoo goo)
            {
                Value = goo.Value?.Duplicate();
                return Value != null;
            }

            return false;
        }
    }

    public sealed class StbSectionGoo : GH_Goo<StbSectionModel>
    {
        public StbSectionGoo()
        {
        }

        public StbSectionGoo(StbSectionModel section)
        {
            Value = section;
        }

        public override bool IsValid => Value != null && Value.Material != null;

        public override string TypeName => "STB Section";

        public override string TypeDescription => "STB section definition";

        public override IGH_Goo Duplicate()
        {
            return new StbSectionGoo(Value?.Duplicate());
        }

        public override string ToString()
        {
            return Value?.ToString() ?? "Null STB Section";
        }

        public override bool CastFrom(object source)
        {
            if (source is StbSectionModel section)
            {
                Value = section;
                return true;
            }

            if (source is StbSectionGoo goo)
            {
                Value = goo.Value?.Duplicate();
                return Value != null;
            }

            return false;
        }
    }

    public sealed class StbElementGoo : GH_Goo<StbElementModel>
    {
        public StbElementGoo()
        {
        }

        public StbElementGoo(StbElementModel element)
        {
            Value = element;
        }

        public override bool IsValid => Value != null && Value.Line.IsValid && Value.Section != null;

        public override string TypeName => "STB Element";

        public override string TypeDescription => "STB frame element";

        public override IGH_Goo Duplicate()
        {
            return new StbElementGoo(Value?.Duplicate());
        }

        public override string ToString()
        {
            return Value?.ToString() ?? "Null STB Element";
        }

        public override bool CastFrom(object source)
        {
            if (source is StbElementModel element)
            {
                Value = element;
                return true;
            }

            if (source is StbElementGoo goo)
            {
                Value = goo.Value?.Duplicate();
                return Value != null;
            }

            return false;
        }
    }

    public sealed class StbSupportGoo : GH_Goo<StbSupportModel>
    {
        public StbSupportGoo()
        {
        }

        public StbSupportGoo(StbSupportModel support)
        {
            Value = support;
        }

        public override bool IsValid => Value != null;

        public override string TypeName => "STB Support";

        public override string TypeDescription => "STB support condition";

        public override IGH_Goo Duplicate()
        {
            return new StbSupportGoo(Value?.Duplicate());
        }

        public override string ToString()
        {
            return Value?.ToString() ?? "Null STB Support";
        }

        public override bool CastFrom(object source)
        {
            if (source is StbSupportModel support)
            {
                Value = support;
                return true;
            }

            if (source is StbSupportGoo goo)
            {
                Value = goo.Value?.Duplicate();
                return Value != null;
            }

            return false;
        }
    }

    public sealed class StbLoadGoo : GH_Goo<StbLoadModel>
    {
        public StbLoadGoo()
        {
        }

        public StbLoadGoo(StbLoadModel load)
        {
            Value = load;
        }

        public override bool IsValid => Value != null;

        public override string TypeName => "STB Load";

        public override string TypeDescription => "STB point, line, or area load";

        public override IGH_Goo Duplicate()
        {
            return new StbLoadGoo(Value?.Duplicate());
        }

        public override string ToString()
        {
            return Value?.ToString() ?? "Null STB Load";
        }

        public override bool CastFrom(object source)
        {
            if (source is StbLoadModel load)
            {
                Value = load;
                return true;
            }

            if (source is StbLoadGoo goo)
            {
                Value = goo.Value?.Duplicate();
                return Value != null;
            }

            return false;
        }
    }

    public sealed class StbMaterialParameter : GH_Param<StbMaterialGoo>
    {
        public StbMaterialParameter()
            : base("Material", "Mat", "STB material", "STB", "Model", GH_ParamAccess.item)
        {
        }

        public override Guid ComponentGuid => new Guid("a1f2c3d4-5e6f-4789-a012-3456789abcde");

        public override GH_Exposure Exposure => GH_Exposure.hidden;

        protected override Bitmap Icon => null;
    }

    public sealed class StbSectionParameter : GH_Param<StbSectionGoo>
    {
        public StbSectionParameter()
            : base("Section", "Sec", "STB section", "STB", "Model", GH_ParamAccess.item)
        {
        }

        public override Guid ComponentGuid => new Guid("b2f3c4d5-6e7f-4890-b123-456789abcdef");

        public override GH_Exposure Exposure => GH_Exposure.hidden;

        protected override Bitmap Icon => null;
    }

    public sealed class StbElementParameter : GH_Param<StbElementGoo>
    {
        public StbElementParameter()
            : base("Element", "Elem", "STB element", "STB", "Model", GH_ParamAccess.item)
        {
        }

        public override Guid ComponentGuid => new Guid("c3f4d5e6-7f80-4901-c234-56789abcdef0");

        public override GH_Exposure Exposure => GH_Exposure.hidden;

        protected override Bitmap Icon => null;
    }

    public sealed class StbSupportParameter : GH_Param<StbSupportGoo>
    {
        public StbSupportParameter()
            : base("Support", "Sup", "STB support", "STB", "Model", GH_ParamAccess.item)
        {
        }

        public override Guid ComponentGuid => new Guid("d4f5e6f7-8091-4012-d345-6789abcdef01");

        public override GH_Exposure Exposure => GH_Exposure.hidden;

        protected override Bitmap Icon => null;
    }

    public sealed class StbLoadParameter : GH_Param<StbLoadGoo>
    {
        public StbLoadParameter()
            : base("Load", "Ld", "STB load", "STB", "Model", GH_ParamAccess.item)
        {
        }

        public override Guid ComponentGuid => new Guid("e5f6a7b8-9102-4234-e456-789abcdef012");

        public override GH_Exposure Exposure => GH_Exposure.hidden;

        protected override Bitmap Icon => null;
    }

    internal static class StbModelGooUtil
    {
        public static bool TryGetMaterial(IGH_DataAccess da, int index, out StbMaterialModel material)
        {
            material = null;
            StbMaterialGoo goo = null;
            if (!da.GetData(index, ref goo) || goo?.Value == null)
            {
                return false;
            }

            material = goo.Value;
            return true;
        }

        public static bool TryGetSection(IGH_DataAccess da, int index, out StbSectionModel section)
        {
            section = null;
            StbSectionGoo goo = null;
            if (!da.GetData(index, ref goo) || goo?.Value == null)
            {
                return false;
            }

            section = goo.Value;
            return true;
        }

        public static List<StbElementModel> GetElements(IGH_DataAccess da, int index)
        {
            var values = new List<StbElementModel>();
            var goos = new List<StbElementGoo>();
            if (da.GetDataList(index, goos))
            {
                foreach (var goo in goos)
                {
                    if (goo?.Value != null)
                    {
                        values.Add(goo.Value);
                    }
                }

                return values;
            }

            StbElementGoo single = null;
            if (da.GetData(index, ref single) && single?.Value != null)
            {
                values.Add(single.Value);
            }

            return values;
        }

        public static List<StbSupportModel> GetSupports(IGH_DataAccess da, int index)
        {
            var values = new List<StbSupportModel>();
            var goos = new List<StbSupportGoo>();
            if (da.GetDataList(index, goos))
            {
                foreach (var goo in goos)
                {
                    if (goo?.Value != null)
                    {
                        values.Add(goo.Value);
                    }
                }

                return values;
            }

            StbSupportGoo single = null;
            if (da.GetData(index, ref single) && single?.Value != null)
            {
                values.Add(single.Value);
            }

            return values;
        }

        public static List<StbLoadModel> GetLoads(IGH_DataAccess da, int index)
        {
            var values = new List<StbLoadModel>();
            var goos = new List<StbLoadGoo>();
            if (da.GetDataList(index, goos))
            {
                foreach (var goo in goos)
                {
                    if (goo?.Value != null)
                    {
                        values.Add(goo.Value);
                    }
                }

                return values;
            }

            StbLoadGoo single = null;
            if (da.GetData(index, ref single) && single?.Value != null)
            {
                values.Add(single.Value);
            }

            return values;
        }
    }
}
