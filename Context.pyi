import copy
import functools
import math
from collections import defaultdict
import Operator as Op
import Polynomial as Poly

'''디폴트함수는 Parameters, Operator 는 무조건 Default, Operands 는 기본적으로 Parameters 와 같은 취급을 하고,
Name attribute 에 함수 이름을 부여하는 것으로 한다.'''


class Function: # Function class

    def __init__(self, parameters =(), operator = Op.Operator(""), *operands):

        self.Parameters = parameters
        self.Operator = operator
        self.Operands = list(operands)

        self.Name = None # 이 부분은 함수 자체의 이름으로 지어줘야 한다. 디폴트함수의 경우 많이 사용하게 될 것.
        # 또한 디폴트함수의 원형은 Name 을 부여하며, DefaultDictionary 에 생성과 함꼐 집어넣어야 한다.
        self.Value = None

        #Isomorphism code
        #self.InverseImage = None

    def __str__(self):

        if self.Operator == Op.DEFAULT: # 수정 내역 6. 디폴트함수의 출력
            return self.Name + "(" + Op.Sigma(*[str(elem) + "," for elem in self.Operands])[:-1] + ")"

        return  str(self.Operator) + "(" + Op.Sigma(*[str(elem) + "," for elem in self.Operands])[:-1] + ")"


    def __call__(self, call_option = False, *args):

        if len(args) != len(self.Parameters): #Funcking false call
            return "Fuck You"
        elif args == self.Parameters: # Default call optimization f(Parameters).
            return self

        elif self == Ln and args[0].Operator == Op.POW and args[0].Operands[0] == E: # Ln(E^x) = x
            return args[0].Operands[1]

        elif self.IsSingle() and args[0].IsSingle() and self.Operator.Inverse == args[0].Operator: # Other Inverse calls
            return args[0].Operands[0]

        else:
            redefined_parameters = Redefine_Parameter(call_option, *args)

            substitution_table = defaultdict(list,dict(zip([i.Name for i in self.Parameters], args)))
            clone = copy.deepcopy(self)
            Substitute(clone, substitution_table)

            # 치환된 것을 Top - down 방식으로 다시 계산하며 축약.
            clone = CalculateTree(clone)

            if isinstance(clone, ConstantMap):
                pass
            else:
                setattr(clone, 'Parameters', redefined_parameters)
            return clone

    def __eq__(self, other): # Merely comparing two function by =. this is "For developer" function.

        if isinstance(self, ConstantMap) and isinstance(other, ConstantMap):
            return self.Value == other.Value

        elif self.Operator == Op.DEFAULT and other.Operator == Op.DEFAULT: # 디폴트 함수의 경우.
            return self.Name == other.Name and self.Operands == other.Operands
        '''
        b = Bind("=", self, other)
        if b is None:
            pass
        else:
            return b
        '''
        return self.Operator == other.Operator and self.Operands == other.Operands
        #같은 것은 같은 것이므로 패러미터는 비교하지 않는다.

    def __add__(self, other):

        if isinstance(self, ConstantMap) and isinstance(other, ConstantMap):
            return ConstantMap(self.Value + other.Value)

        '''
        b = Bind("+", self, other)
        if not b is None:
            return b
        '''

        f = Remove_Parenthesis(Op.ADD, self, other)
        f = Order_operands(f)
        f = Group_operands(f)
        return f

    #Syntactic sugar
    def __sub__(self, other):
        if self == other:
            return ZERO

        '''
        b = Bind("-", self, other)
        if not b is None:
            return b
        '''
        return self + NEG_ONE*other

    def __mul__(self, other):

        if isinstance(self, ConstantMap) and isinstance(other, ConstantMap):
            return ConstantMap(self.Value * other.Value)

        '''
        b = Bind("*", self, other)
        if not b is None:
            return b
        '''

        f = Remove_Parenthesis(Op.MUL, self, other)
        f = Order_operands(f)
        f = Group_operands(f)
        return f


    def __pow__(self, power, modulo=None):

        if isinstance(self, ConstantMap) and isinstance(power, ConstantMap):
            return ConstantMap(pow(self.Value, power.Value))

        elif self == E and power.Operator == Op.LN: # E^(Ln(x)) = x
            return power.Operands[0]
        '''
        b = Bind("^", self, power)
        if not b is None:
            return b
        '''
        f = Remove_Parenthesis(Op.POW, self, power)
        f = Order_operands(f)
        f = Group_operands(f)
        return f

    #Syntactic sugar
    def __truediv__(self, other):
        if other == ZERO:
            return ZeroDivisionError
        elif self == ZERO:
            return ZERO
        elif self == other:
            return ONE
        else:
            '''
            b = Bind("/", self, other)
            if not b is None:
                return b
            '''
            return self * pow(other, NEG_ONE)

    # (Partial) Differentiation Operator Del.
    def Del(self, other):

        if not isinstance(other, IdentityMap):
            return "Fuck You"

        else:
            if IsConst(self, (other,)):
                return ZERO

            elif self == other:
                return ONE

            elif self.Operator == Op.DEFAULT and self.Operands == list(self.Parameters): # 수정 내역 1 : 디폴트함수의 미분은 디폴트
                return Function(self.Parameters, Op.DEL, self, other) #  이런 경우에 DEL 을 !

            elif self == Sin(False, other):
                return Cos(False, other)

            elif self == Cos(False, other):
                return NEG_ONE * Sin(False, other)

            elif self == Ln(False, other):
                return ONE/other

            elif self == Arcsin(False, other):
                return pow( ONE - pow(other, ConstantMap(2)) ,ConstantMap(-1/2))

            elif self == Arccos(False, other):
                return NEG_ONE * pow( ONE - pow(other, ConstantMap(2)) ,ConstantMap(-1/2))

            elif self.Operator == Op.ADD:
                return Op.Sigma(*[i.Del(other) for i in self.Operands])

            elif self.Operator == Op.MUL:

                l = self.Operands[0]
                r = Function(self.Parameters, Op.MUL, *self.Operands[1:])
                if len(r.Operands) == 1:
                    r = r.Operands[0]

                return l.Del(other) * r + l * r.Del(other)

            elif self.Operator == Op.POW:

                base = self.Operands[0]
                exponent = self.Operands[1]
                if IsConst(exponent, (other,)): # 수정 내역 #3: IsConst 를 사용
                    return exponent * base.Del(other) * pow(base, exponent-ONE)
                else:
                    p = pow(base, exponent-ONE)
                    q = exponent * base.Del(other) + base * Ln(False, base) * exponent.Del(other)
                    return p * q

            elif self.IsUnitary():
                # chain rule
                p = self.Operands
                q = None
                if self.Operator == Op.DEFAULT:
                    q = DefaultDictionary[self.Name]
                else:
                    q = UnitaryDictionary[self.Operator]
                return Op.Sigma(*[p[i].Del(other) * q.Del(q.Parameters[i])(False, *p) for i in range(len(p))])
                pass

            else:
                return None

    def IsUnitary(self): # Unitary ( Irreducible ) Function

        return self.Operator.Name in Op.Operator.UnitaryNames

    def IsSingle(self): # Single Variable Unitary Func

        return self.IsUnitary() and len(self.Parameters) == 1


class ConstantMap(Function):

    def __init__(self, value):

        Function.__init__(self, (), Op.CONST, self)
        self.Value = value
        #self.InverseImage = Poly.Polynomial([self.Value])

    def __call__(self, call_option = False, *args):

        return self

    def __str__(self):
        return str(self.Value)

#Identity map. Used for parametrization
class IdentityMap(Function):

    def __init__(self, letter):

        Function.__init__(self, (self,) , Op.IDENTITY, self)
        self.Name = letter

    def __eq__(self, other):

        return self.Name == other.Name

    # Warning: 이 코드는 본질을 흐린다. Function class 의 비교에는 사실 등식 밖에 없다. 부등호들은 편의상 도입한 것이며 실제 부등식 기능과는 관련이 없다.
    # 이것들은 인자의 우선 순위를 나타내는 것으로, ascii 비교의 정반대: x 가 y 보다 우선한다.
    def __gt__(self, other):

        return self.Name < other.Name

    def __lt__(self, other):

        return self.Name > other.Name

    def __hash__(self):

        return ord(self.Name)

    def __call__(self, call_option = False, *args):

        if len(args)!=1:
            return "Fuck You"

        return args[0]

    def __str__(self):

        return self.Name

# Default Function Generator.
def DefaultFunction(name, parameters):
    f = Function(parameters, Op.DEFAULT, *list(parameters))
    setattr(f, "Name" , name)
    DefaultDictionary[name] = f
    return f

#lemma code
def Substitute(function, substitution_table):

    ops = function.Operands

    for x in range(len(ops)):

        if isinstance(ops[x], IdentityMap):
            name = ops[x].Name
            arg = substitution_table[name]
            if not arg:
                pass
            else:
                ops[x] = arg

        elif isinstance(ops[x], ConstantMap):
            pass

        else:
            Substitute(ops[x], substitution_table)

#lemma code
def IsConst(function, reference = ()):
    # reference X -> To check if it is literally constant
    # reference O -> To check if it is constant with respect to reference variables

    if isinstance(function, ConstantMap):
        return True

    elif isinstance(function, IdentityMap):
        if not reference:
            return False
        else:
            if function in reference:
                return False
            else:
                return True

    else:
        ops = function.Operands
        for x in range(len(ops)):
            if not IsConst(ops[x]):
                return False
            else:
                pass

        return True

# Default function call like f(0), is Const but cannot be computed. 이런 구분은 짜증나는 것이지만, 현재로서 방법이 없다.
def IsPureConst(const_tree):

    if not IsConst(const_tree):
        return False
    elif isinstance(const_tree, ConstantMap):
        return True

    elif const_tree.Operator == Op.DEFAULT:
        return False

    else:
        ops = const_tree.Operands
        for x in range(len(ops)):
            if not IsPureConst(ops[x]):
                return False
            else:
                pass

        return True

#lemma code
def EvaluateConst(const_tree): # Evaluating real value of Constant Tree. This should be done on Pure constant Tree.

    if isinstance(const_tree, ConstantMap):
        return const_tree
    else:
        op = const_tree.Operator
        if not const_tree.IsUnitary():
            return op.EvaluationFunction(*[EvaluateConst(i) for i in const_tree.Operands])

        else:
            return ConstantMap(op.EvaluationFunction(*[EvaluateConst(i).Value for i in const_tree.Operands]))

#lemma code
def CalculateTree(function):

        if IsPureConst(function):
            return EvaluateConst(function)
        elif IsConst(function):
            return function
        elif isinstance(function, IdentityMap) or function.Operator == Op.DEFAULT:
            return function
        elif function.IsUnitary():
            return Function(function.Parameters, function.Operator, *[CalculateTree(i) for i in function.Operands])
        else:
            op = function.Operator
            if op == Op.ADD:
                return Op.Sigma(*[CalculateTree(elem) for elem in function.Operands])
            elif op == Op.MUL:
                return Op.Product(*[CalculateTree(elem) for elem in function.Operands])
            elif op == Op.POW:
                return pow(CalculateTree(function.Operands[0]), CalculateTree(function.Operands[1]))

            # Should add Unitary Function - related simplification rule here. like sin^2 + cos^2 = 1..


'''
#lemma code
def IsPolynomial(function):

    if isinstance(function, ConstantMap):
        return True
    elif isinstance(function, IdentityMap):
        return True
    elif function.Operator.IsUnitary():
        return False

    else:
        ops = function.Operands
        for x in range(len(ops)):
            if not IsPolynomial(ops[x]):
                return False
            else:
                pass
        return True
'''



# Fundamental Variable X used for built - in Unitary Functions.
VarX = IdentityMap("x")

#setattr(VarX, "InverseImage", Poly.Polynomial([1]))
#이것은 임시방편이다. 곧 Polynomial 클래스를 Multi-variable version 으로 확장할 것이니 그때까지만 놔두자.

VarY = IdentityMap("y")
VarZ = IdentityMap("z")
VarT = IdentityMap("t")

# Four basic Built - in Functions.
Sin = Function((VarX,), Op.SIN, VarX)
Cos = Function((VarX,), Op.COS, VarX)
Ln = Function((VarX,), Op.LN, VarX)

Arcsin = Function((VarX,), Op.ARCSIN, VarX)
Arccos = Function((VarX,), Op.ARCCOS, VarX)
UnitaryDictionary = {Op.SIN : Sin, Op.COS : Cos, Op.LN : Ln, Op.ARCSIN : Arcsin, Op.ARCCOS : Arccos}
DefaultDictionary = {}

# Fundamental Constants used frequently.
ONE = ConstantMap(1)
NEG_ONE = ConstantMap(-1)
ZERO = ConstantMap(0)
PI = ConstantMap(math.pi)
E = ConstantMap(math.e)

# Example of Default Function.
Mine = DefaultFunction("Mine", (VarX, VarY))

#lemma code.
def Redefine_Parameter(call_option = False, *function_set):

        if call_option: # False if not explicitly given parameter order
            redefined_parameters = (IdentityMap(i) for i in call_option)

        else:
            redefined_parameters = tuple(set(functools.reduce(lambda x,y : x + y , (i.Parameters for i in function_set))))

        return redefined_parameters


#lemma code
def Remove_Parenthesis(operator, function1, function2):

        redefined_parameters = Redefine_Parameter(False, function1, function2)
        parenthesis_removed_form = ZERO

        if operator == Op.ADD or operator == Op.MUL:
            if function1.Operator == operator and function2.Operator == operator:
                return Function(redefined_parameters, operator, *(copy.deepcopy(function1.Operands) + copy.deepcopy(function2.Operands)))
            elif function1.Operator == operator:
               return Function(redefined_parameters, operator, *(copy.deepcopy(function1.Operands) + [copy.deepcopy(function2)]))
            elif function2.Operator == operator:
                return Function(redefined_parameters, operator, *([copy.deepcopy(function1)] + copy.deepcopy(function2.Operands)))

        elif operator == Op.POW:
            if function1.Operator ==  operator:
                return Function(redefined_parameters, operator, function1.Operands[0] * function2)

        parenthesis_removed_form = Function(redefined_parameters, operator, copy.deepcopy(function1), copy.deepcopy(function2))

        return parenthesis_removed_form

#lemma code
def Order_operands(function):

    if function.Operator == Op.POW:
        if function.Operands[0] == ONE or function.Operands[1] == ZERO:
            return ONE
        elif function.Operands[0] == ZERO:
            return ZERO
        elif function.Operands[1] == ONE:
            return function.Operands[0]
        else:
            return function

    elif function.Operator == Op.ADD or function.Operator == Op.MUL:

        constant_operands = [elem for elem in function.Operands if IsPureConst(elem)]
        # 수정 내역 5. Pure ConstantMap 인 것에 대해서만 축약 적용.
        non_constant_operands = [elem for elem in function.Operands if not elem in constant_operands]

        pre = None
        if constant_operands:
            pre = ConstantMap(function.Operator.EvaluationFunction(*[EvaluateConst(C).Value for C in constant_operands]))

        temp = non_constant_operands

        if function.Operator == Op.ADD:

            if pre is None or pre == ZERO:
                function.Operands = []
            else:
                function.Operands = [pre,]
                pass

            ln_operators = [elem for elem in temp if elem.Operator == Op.LN]
            if not ln_operators:
                pass
            else: # Ln(a) + Ln(b) = Ln(ab) If well - defined. This needs more discussion, since Ln is well defined for only positive number.
                temp = [elem for elem in temp if not elem in ln_operators]
                ln = Ln(False, Op.Product(*[elem.Operands[0] for elem in ln_operators]))
                temp += [ln,]
                # Ln(a^x) = xLn(a) 는 Default 로서는 '넣지 않는다'. 지수보다 상수가 편하다고 생각하는 철학? ㅎㅎ.

        elif function.Operator == Op.MUL:

            if pre is None or pre == ONE:
                function.Operands = []
            elif pre == ZERO:
                return ZERO
            else:
                function.Operands = [pre,]
                pass

        identity_operands = [elem for elem in temp if isinstance(elem, IdentityMap)]
        others = [elem for elem in temp if (elem not in identity_operands)]
        temp = sorted(identity_operands) + others

        function.Operands += temp

        if len(function.Operands) == 1:
            return function.Operands[0]
        else:
            return function
    else:
        return function

#lemma code.
def Group_operands(function):

    # For Only 2 multiplied terms
    if function.Operator == Op.ADD:
        lefts = []
        for elem in function.Operands:
            if elem.Operator == Op.MUL and len(elem.Operands) == 2:
                #Identity Map takes priority 1st.
                if isinstance(elem.Operands[0], IdentityMap) and isinstance(elem.Operands[1], IdentityMap):
                    lefts.append((max(elem.Operands), min(elem.Operands)))
                elif isinstance(elem.Operands[0], IdentityMap):
                    lefts.append((elem.Operands[0], elem.Operands[1]))
                elif isinstance(elem.Operands[1], IdentityMap):
                    lefts.append((elem.Operands[1], elem.Operands[0]))
                #And Unitary Functions.
                elif elem.Operands[0].IsUnitary() and not elem.Operands[1].IsUnitary():
                    lefts.append((elem.Operands[0], elem.Operands[1]))
                elif elem.Operands[1].IsUnitary() and not elem.Operands[0].IsUnitary():
                    lefts.append((elem.Operands[1], elem.Operands[0]))
                else:
                    lefts.append((elem, ONE))
            else:
                lefts.append((elem, ONE))

        grouped_list = []

        while lefts:

            pop = lefts[0][0]
            temp = [elem[1] for elem in lefts if elem[0] == pop]
            grouped_list.append((pop, Op.Sigma(*temp)))
            lefts = [elem for elem in lefts if elem[0] != pop]

        function.Operands = [elem[0] * elem[1] for elem in grouped_list]

        if len(function.Operands) == 1:
            return function.Operands[0]


    elif function.Operator == Op.MUL:

        bases = []
        for elem in function.Operands:
            if elem.Operator == Op.POW:
                    bases.append((elem.Operands[0], elem.Operands[1]))
            else:
                bases.append((elem, ONE))


        grouped_list = []

        while bases:
            pop = bases[0][0]
            temp = [elem[1] for elem in bases if elem[0] == pop]
            grouped_list.append((pop, Op.Sigma(*temp)))
            bases = [elem for elem in bases if elem[0] != pop]

        #Here, I thought about b^x * c^x = (bc)^x, only true for b, c>= 0, Thus I wouldn't add this.
        function.Operands = [pow(elem[0], elem[1]) for elem in grouped_list]

        if len(function.Operands) == 1:
            return function.Operands[0]

    return function


'''Isomorphism 은 분명 좋은 수학적 도구이나, 이를 코드로 쓰기에는 그 자유도 때문에 매우 위험하다.
    아래의 코드가 정말로 옳은 방법인지 반드시 나중에 확인할 필요가 있다.'''

'''
#Isomorphism code
class Isomorphism:

    def __init__(self, mapping, *operator_names):

        self.Map = mapping
        self.Operations = operator_names


#Isomorphism code
def Convert(self, parameter):

    #Monomorphism: Polynomial -> Function.
    summation = [Function((parameter, ), Op.MUL,
                                ConstantMap(self.Coefficients[i]), Function((parameter,), Op.POW, parameter, ConstantMap(i)))
                    for i in range(self.Degree + 1)]

    a = ZERO
    if len(summation) == 1:
        a = summation[0]
    else:
        a = Function((parameter,), Op.ADD, *summation)
    setattr(a, "InverseImage", self)
    return a
# 곧 다항식 모듈을 일반적으로 n 변수 다항식으로 바꿀 테니 그때까지만 참자.


#Isomorphism code
Poly.Polynomial.ConvertToFunction = Convert
Polynomial_Isomorphism = Isomorphism(Poly.Polynomial.ConvertToFunction, "=", "+", "*", "-")
Isomorphisms_list = { Function : None, Poly.Polynomial : Polynomial_Isomorphism }


#Isomorphism code
def Bind(operator_name, function1, function2):

    f1 = function1.InverseImage
    f2 = function2.InverseImage

    if f1 is None or f2 is None:
        return None
    elif isinstance(f1, type(f2)):
        i = Isomorphisms_list[type(f2)]
    elif isinstance(f2, type(f1)):
        i = Isomorphisms_list[type(f1)]


    if i is None or not (operator_name in i.Operations):
        return None
    elif operator_name == "+":
        return i.Map(f1 + f2, Redefine_Parameter(False, function1, function2))
    elif operator_name == "*":
        return i.Map(f1 * f2, Redefine_Parameter(False, function1, function2))
    elif operator_name == "=":
        return f1 == f2
    elif operator_name == "/":
        return i.Map(f1/f2, Redefine_Parameter(False, function1, function2))
    elif operator_name == "-":
        return i.Map(f1 - f2, Redefine_Parameter(False, function1, function2))
    elif operator_name == "^":
        return i.Map(pow(f1, f2), Redefine_Parameter(False, function1, function2))
    else:
        return None
'''

Tan = Sin/Cos
Sec = ONE/Cos
Csc = ONE/Sin
Cot = ONE/Tan
Log = Ln(False, VarX)/Ln(False, VarY) # Log_x(y). this needs more discussion.


Fx = ConstantMap(4) * VarY * VarZ * VarY * pow(VarZ, ConstantMap(3))
Qx = VarY + VarY
Tx = ConstantMap(4) * pow(VarX, ConstantMap(2)) + VarY
Gx = Sin(False, Tx)
DisGustingFunction = pow(VarX, VarX)
Fucked_at_Zero = ONE/VarX
SinCos = Sin(False, VarX) * Cos(False, VarX)
ExpSin = pow(E, Sin(False, VarX))
TripleVariableDude = (pow(VarX, ConstantMap(2)) + VarY * VarZ) / (ONE - VarX * Ln(False, VarZ))
Monster = TripleVariableDude(False, VarT, VarT, VarT)

'''
print(Ln(False, pow(E, ConstantMap(2))))
print(Fx)
print(Qx)

print(Gx)
print(Gx.Del(VarX))

print(DisGustingFunction.Del(VarX))
print(Fucked_at_Zero * VarX)
print(SinCos.Del(VarX))
print(ExpSin.Del(VarX))
print(Tan.Del(VarX))
print(Sec.Del(VarX))
print(TripleVariableDude)
print(Monster)
print(Mine(False, ZERO, ZERO) + ConstantMap(2) * Mine(False, ZERO, ZERO) + Sin(False, ONE))
'''

























