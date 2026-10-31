# Netting Applicator

Fusion 360 script that generates a meat-netting applicator for salumi, modelled on the
Browin 310090: a tube with a bell-mouth entry, a round flange cut flat at the bottom,
and a flat foot under the tube.

## Use on a counter
Stand it on the foot with the flange flush to the counter edge and the mouth facing you.
Clamp the two foot ears down with small C-clamps (or screw through the ear holes).
Bunch the netting on the outside of the tube, push the meat into the mouth, and it comes
out the far end netted, onto the counter.

## Printing
Print mouth-down (flange flat on the bed). Every surface overhangs 45 degrees or less, so
no supports are needed. Footprint is about 172 x 160 mm, 156 mm tall. PETG is a good choice
for food contact and hot-water washing.

## Generate the model
1. Copy `NettingApplicator/` into `%APPDATA%\Autodesk\Autodesk Fusion 360\API\Scripts\`.
2. In Fusion: Utilities > Add-Ins > Scripts and Add-Ins > NettingApplicator > Run.
3. Change dimensions (mm) at the top of `NettingApplicator.py` and re-run.
