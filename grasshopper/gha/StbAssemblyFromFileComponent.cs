using System;
using System.Drawing;
using Grasshopper.Kernel;

namespace StbGrasshopper
{
    public sealed class StbAssemblyFromFileComponent : GH_Component
    {
        public StbAssemblyFromFileComponent()
            : base(
                "STb Assembly from file",
                "STb File",
                "Read an existing STB DAT file and create a typed STb Model.",
                "STB",
                "Model")
        {
        }

        public override Guid ComponentGuid => new Guid("a8b9c0d1-2345-4567-89ab-cdef01234567");
        protected override Bitmap Icon => StbIcons.Assemble;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddTextParameter("DAT Path", "DAT", "Path to an existing STB .dat file.", GH_ParamAccess.item);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbModelParameter(), "STb Model", "STb Model", "Typed STb Model read from the DAT file.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            string datPath = null;
            if (!da.GetData(0, ref datPath))
            {
                return;
            }

            try
            {
                da.SetData(0, new StbModelGoo(StbDatModelReader.Read(datPath)));
            }
            catch (Exception ex)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Failed to read STB DAT file: " + ex.Message);
            }
        }
    }
}
