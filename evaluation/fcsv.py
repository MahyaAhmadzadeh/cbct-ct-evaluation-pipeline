import re
import argparse

def create_fcsv(cxt_filepath, fcsv_filepath, csv_filepath):
    
    cxt_file = open(cxt_filepath, 'r')
    fcsv_file = open(fcsv_filepath, "w")
    csv_file = open(csv_filepath, "w")
    metadata = """# numPoints = 4
# symbolScale = 5
# symbolType = 12
# visibility = 1
# textScale = 4.5
# color = 0.4,1,1
# selectedColor = 1,0.5.0.5
# opacity = 1
# ambient = 0
# diffuse = 1
# specular = 0
# power = 1
# locked = 0
# numberingScheme = 0
# columns = label,x,y,z,sel,vis
    """
    count = 0
    regex = r"[+-]?\d+(?:\.\d+)?"
    fcsv_file.write(metadata)
    cxt_contents = cxt_file.readlines()
    OG = cxt_contents[7].split()
    ox, oy, oz = float(OG[1]), float(OG[2]), float(OG[3])

    SP = cxt_contents[9].split()
    spx, spy, spz = float(SP[1]), float(SP[1]), float(SP[1])
    print(SP)

    cxt_contents = cxt_contents[28:]
    print(len(cxt_contents))

    for cxt_content in cxt_contents:
        cxt_content = cxt_content[10:].split("\\")
        x, y, z = cxt_content[0::3], cxt_content[1::3], cxt_content[2::3]

        for i in range(len(x)):
            if i%25==0:
                a, b, c = x[i], y[i], z[i]
                a, b, c = re.findall(regex, a)[0], re.findall(regex, b)[0], re.findall(regex, c)[0]
                a, b, c = -float(a), -float(b), float(c)
                line = f"{count}, {a}, {b}, {c}, 1, 1\n"
                fcsv_file.write(line)

                a, b, c = round((a-ox)/spx), round((b-ox)/spy), round((c-ox)/spz)
                line = f"{a}, {b}, {c}\n"
                csv_file.write(line)
                
                count+=1

    fcsv_file.close()
    csv_file.close()
    cxt_file.close()
    print(count)


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cxt_filepath", type=str, help="All patient dits in glob format")
    parser.add_argument("--fcsv_filepath", type=str, help="All patient dits in glob format")
    parser.add_argument("--csv_filepath", type=str, help="All patient dits in glob format")

    args = parser.parse_args()
    create_fcsv(args.cxt_filepath, args.fcsv_filepath, args.csv_filepath)