#if UNITY_EDITOR
using System;
using System.IO;
using System.Runtime.Serialization;
using UnityEditor;
using UnityEngine;

public static class ItemPreviewRegressionCheck
{
    [MenuItem("Tools/NRO/Check item preview isolation")]
    public static void Run()
    {
        string directory = Path.Combine(Path.GetTempPath(), "nro-item-identity");
        Directory.CreateDirectory(directory);
        try
        {
            Char actor = (Char)FormatterServices.GetUninitializedObject(typeof(Char));
            actor.head = 1; actor.body = 2; actor.leg = 3; actor.bag = -1;
            actor.setPartOld();
            actor.setPartTemp(10, 20, 30, 40);
            actor.setPartOld(); // Reopening a preview must keep the real base.
            actor.setPartTemp(11, -1, -1, -1);
            Require(actor.head == 11 && actor.body == 2 && actor.leg == 3 && actor.bag == -1, "partial preview retained previous outfit");
            actor.setPartTemp(-1, -1, -1, -1);
            Require(actor.head == 1 && actor.body == 2 && actor.leg == 3 && actor.bag == -1, "empty mapping retained previous outfit");
            actor.resetPartTemp();
            Require(actor.head == 1 && actor.body == 2 && actor.leg == 3 && actor.bag == -1, "closing preview did not restore empty bag");
            actor.head = 5; actor.body = 6; actor.leg = 7; actor.bag = 8;
            actor.setPartTemp(12, -1, -1, -1);
            actor.resetPartTemp();
            Require(actor.head == 5 && actor.body == 6 && actor.leg == 7 && actor.bag == 8, "new preview did not use current equipped state");
            actor.setPartOld();
            actor.head = 20; actor.body = 21; actor.leg = 22;
            actor.updatePartPreviewBase(20, 21, 22);
            actor.updateBagPreviewBase(-1);
            actor.setPartTemp(30, -1, -1, -1);
            actor.resetPartTemp();
            Require(actor.head == 20 && actor.body == 21 && actor.leg == 22 && actor.bag == -1, "equipping during preview restored obsolete outfit");
            File.WriteAllText(Path.Combine(directory, "preview-regression.json"), "{\"passed\":true,\"checks\":5}");
            Debug.Log("NRO item preview isolation: 5 checks passed");
        }
        catch (Exception error)
        {
            File.WriteAllText(Path.Combine(directory, "preview-regression.json"), "{\"passed\":false}");
            Debug.LogException(error);
        }
    }

    private static void Require(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }
}
#endif
