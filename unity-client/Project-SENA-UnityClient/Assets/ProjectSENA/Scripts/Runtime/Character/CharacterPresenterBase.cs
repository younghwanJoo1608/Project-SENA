using UnityEngine;

namespace ProjectSENA.Character
{
    public abstract class CharacterPresenterBase : MonoBehaviour
    {
        public abstract void ApplyPresentation(SenaCharacterPresentation presentation);
    }
}
