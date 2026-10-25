// Synthetic source template. Build outside the mod manager with the matching SDK.
#include <Mod/CppUserModBase.hpp>

class ExampleNative final : public RC::CppUserModBase
{
public:
    ExampleNative()
    {
        ModName = STR("ExampleNative");
        ModVersion = STR("0.1.0");
        ModDescription = STR("Synthetic manager authoring template");
        ModAuthors = STR("Your name");
    }
};

extern "C" __declspec(dllexport) RC::CppUserModBase* start_mod()
{
    return new ExampleNative();
}

extern "C" __declspec(dllexport) void uninstall_mod(RC::CppUserModBase* instance)
{
    delete instance;
}
